from app.database import supabase

contract = {
    "file_name": "test_contract.pdf",
    "original_file_name": "test_contract.pdf",
    "file_type": "application/pdf",
    "status": "uploaded"
}

response = (
    supabase
    .table("contracts")
    .insert(contract)
    .execute()
)

print("Contract inserted successfully!")
print(response.data)