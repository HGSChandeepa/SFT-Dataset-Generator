Usage Examples:

# 1. Save default prompts template

python sft_dataset_generator.py --save-prompts prompts.json

# 2. Generate dataset with API key

export GEMINI_API_KEY="your-api-key"

for windows

$env:GEMINI_API_KEY="your-api-key"

python sft_dataset_generator.py users.sql objectives.md

# 3. Generate with custom settings

python sft_dataset_generator.py users.sql objectives.md \
 --api-key "your-key" \
 -n 500 \
 -o my_dataset.jsonl \
 --temperature 0.8

# 4. Use custom prompts

python sft_dataset_generator.py users.sql objectives.md \
 --prompts custom_prompts.json \
 --batch-size 5

Quick Test:

# Install dependencies

pip install google-generativeai sqlparse

# Set API key

export GEMINI_API_KEY="your-key-here"

# Generate a small test dataset

python sft_dataset_generator.py users.sql objectives.md -n 50
