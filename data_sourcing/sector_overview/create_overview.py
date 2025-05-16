import pandas as pd

# Load all CSV files
common_voice = pd.read_csv('whisper_common_voice_evaluated.csv')
training_hours = pd.read_csv('whisper_training_hours.csv')
fleurs = pd.read_csv('whisper_fleurs_evaluation.csv')
voxpopuli = pd.read_csv('whisper_voxpopuli_evaluated.csv')

# Rename columns for clarity
common_voice = common_voice.rename(columns={
    'Whisper Large-v2': 'whisper_large_v2_common_voice',
    'Whisper Tiny': 'whisper_tiny_common_voice',
    'Whisper Base': 'whisper_base_common_voice',
    'Whisper Small': 'whisper_small_common_voice',
    'Whisper Medium': 'whisper_medium_common_voice',
    'Whisper Large': 'whisper_large_common_voice'
})

fleurs = fleurs.rename(columns={
    'Whisper Large-v2': 'whisper_large_v2_fleurs',
    'Whisper Tiny': 'whisper_tiny_fleurs',
    'Whisper Base': 'whisper_base_fleurs',
    'Whisper Small': 'whisper_small_fleurs',
    'Whisper Medium': 'whisper_medium_fleurs',
    'Whisper Large': 'whisper_large_fleurs'
})

voxpopuli = voxpopuli.rename(columns={
    'Whisper Large-v2': 'whisper_large_v2_voxpopuli',
    'Whisper Tiny': 'whisper_tiny_voxpopuli',
    'Whisper Base': 'whisper_base_voxpopuli',
    'Whisper Small': 'whisper_small_voxpopuli',
    'Whisper Medium': 'whisper_medium_voxpopuli',
    'Whisper Large': 'whisper_large_voxpopuli'
})

# Merge all datasets
merged = pd.merge(common_voice, fleurs, on='Language', how='outer')
merged = pd.merge(merged, voxpopuli, on='Language', how='outer')
merged = pd.merge(merged, training_hours, on='Language', how='outer')

# Reorder columns
columns_order = ['Language', 'Hours'] + sorted([col for col in merged.columns if col not in ['Language', 'Hours']])
merged = merged[columns_order]

# Save to new CSV with empty values for missing data
merged.to_csv('whisper_large_v2_overview.csv', index=False, na_rep='') 