from supabase import create_client
from supabase_config import SUPABASE_URL, SUPABASE_KEY

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Query the download_status table
response = supabase.table('download_status').select('video_duration_seconds').limit(1).execute()

print("\nTrying to access video_duration_seconds column...")
print("Response data:", response.data) 