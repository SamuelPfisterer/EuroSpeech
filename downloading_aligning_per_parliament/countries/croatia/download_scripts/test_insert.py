from supabase import create_client
from supabase_config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Try to insert a test record
test_data = {
    'parliament_id': 'test',
    'session_id': 'test_session',
    'video_status': 'pending',
    'transcript_status': 'pending',
    'video_duration_seconds': 120  # Test with a simple integer value
}

print("Attempting to insert test record...")
response = supabase.table('download_status').insert(test_data).execute()
print("Response:", response.data) 