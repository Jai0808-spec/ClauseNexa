/**
 * Live end-to-end UI test: renders the real <App/>, uses the real api.js and
 * talks to a RUNNING backend (so it also exercises CORS, the upload ->
 * process -> analysis -> ask pipeline and the database).
 *
 * Skipped unless REACT_APP_LIVE_TEST=1, because it needs the backend on
 * http://localhost:8000 and takes about a minute. From frontend/:
 *
 *   set REACT_APP_LIVE_TEST=1            (PowerShell: $env:REACT_APP_LIVE_TEST=1)
 *   npx react-scripts test --watchAll=false --testURL=http://localhost:3000 App.live
 *
 * --testURL matters: the backend only allows the origin http://localhost:3000.
 */

import '@testing-library/jest-dom';
import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const fs = require('fs');
const path = require('path');
const util = require('util');

global.TextEncoder = util.TextEncoder;
global.TextDecoder = util.TextDecoder;

const App = require('./App').default;

const live = process.env.REACT_APP_LIVE_TEST === '1';
const FILE_NAME = 'ui_test_nda.docx';
const DOCX = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document';
const SLOW = 180000;

(live ? describe : describe.skip)('ClauseNexa UI against the live backend', () => {
  jest.setTimeout(10 * SLOW);

  test('upload -> overview -> clause analysis -> ask -> delete', async () => {
    window.confirm = () => true;

    const bytes = fs.readFileSync(
      path.resolve(__dirname, '../../tests/eval/contracts/eval_nda.docx')
    );
    const file = new File([bytes], FILE_NAME, { type: DOCX });

    const { container } = render(<App />);

    // 1. Upload page loads and lists contracts from the backend (CORS + GET /contracts)
    expect(await screen.findByText('Uploaded Contracts')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('Loading...')).not.toBeInTheDocument(), {
      timeout: 30000,
    });

    // 2. Choose a file and upload it (POST /upload, POST /process, GET /contract)
    userEvent.upload(container.querySelector('input[type="file"]'), file);
    userEvent.click(await screen.findByText('Upload to ClauseNexa'));

    // 3. Lands on the Overview page for that contract, with ML summary cards
    expect(
      await screen.findByText(`Analysis Report: ${FILE_NAME}`, {}, { timeout: SLOW })
    ).toBeInTheDocument();
    expect(await screen.findByText('Overall Risk', {}, { timeout: SLOW })).toBeInTheDocument();
    expect(screen.getByText('Clauses')).toBeInTheDocument();
    expect(screen.getByText('Needs Review')).toBeInTheDocument();

    // 4. Clause Analysis page shows classified clauses with risk badges
    userEvent.click(screen.getByText('Clause Analysis'));
    expect(await screen.findByText('Clause Breakdown')).toBeInTheDocument();
    await waitFor(
      () => expect(document.querySelectorAll('.clause-card').length).toBeGreaterThan(0),
      { timeout: SLOW }
    );
    expect(screen.getByText(/not legal advice/i)).toBeInTheDocument();

    // 5. Ask page: question goes to the RAG endpoint and an answer + sources come back
    userEvent.click(screen.getByText('Ask Contract'));
    const box = await screen.findByPlaceholderText('Ask a question about the contract...');
    userEvent.type(box, 'How quickly must confidential information be returned on request?');
    userEvent.click(box.closest('form').querySelector('button[type="submit"]'));

    // The answer and its source text both mention 14 days
    const matches = await screen.findAllByText(/14 days/i, {}, { timeout: SLOW });
    expect(matches.length).toBeGreaterThanOrEqual(2);
    expect(await screen.findByText(/Sources:/, {}, { timeout: 5000 })).toBeInTheDocument();

    // Each source is expandable and carries the exact contract text for verification
    const sourceTexts = Array.from(document.querySelectorAll('.source-text')).map((n) => n.textContent);
    expect(sourceTexts.length).toBeGreaterThan(0);
    expect(sourceTexts.some((t) => /within 14 days/i.test(t))).toBe(true);

    // 6. Off-topic question is refused, not answered from general knowledge
    userEvent.type(box, 'Who is the CEO of Apple?');
    userEvent.click(box.closest('form').querySelector('button[type="submit"]'));
    await waitFor(
      () => expect(screen.queryAllByText(/not (provide|find)|could not find/i).length).toBeGreaterThan(0),
      { timeout: SLOW }
    );
    expect(screen.queryByText(/Tim Cook/i)).not.toBeInTheDocument();

    // 7. Delete the test contract through the UI (DELETE /contracts/{id})
    userEvent.click(screen.getByText('Upload'));
    const row = (await screen.findByText(FILE_NAME)).closest('li');
    userEvent.click(within(row).getByText('Delete'));
    await waitFor(() => expect(screen.queryByText(FILE_NAME)).not.toBeInTheDocument(), {
      timeout: 30000,
    });
  });
});
