# SFT Dataset Generator with Gemini 2.0 Flash

A production-ready Python script that automatically generates high-quality supervised fine-tuning (SFT) datasets for chat-based language models using Google's Gemini 2.0 Flash API. Compatible with TRL (Transformer Reinforcement Learning) and Hugging Face Transformers.

## Features

**Generic SQL Parsing** - Works with any database schema  
**Gemini-Powered Generation** - Uses advanced AI to create diverse, realistic data  
**Customizable Prompts** - External prompt configuration for full control  
**Multiple Question Types** - Schema, record, analytical, and conversational queries  
**Quality Assurance** - Automatic deduplication and validation  
**TRL Compatible** - Ready for immediate use with SFTTrainer  
**Batch Processing** - Efficient API usage with configurable batch sizes  
**Production Ready** - Error handling, retries, and comprehensive logging

## Installation

### Prerequisites

```bash
# Python 3.8 or higher
python --version

# Install required packages
pip install google-generativeai sqlparse
```

### Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Set it as an environment variable:

```bash
export GEMINI_API_KEY="your-api-key-here"
```

## Quick Start

### 1. Prepare Your Files

Create two input files:

**users.sql** - Your database schema and data:

```sql
CREATE TABLE users (
    id INT PRIMARY KEY,
    name VARCHAR(100),
    email VARCHAR(100)
);

INSERT INTO users VALUES (1, 'Alice', 'alice@example.com');
```

**objectives.md** - Your fine-tuning objectives:

```markdown
## Domain

Customer support

## Business Context

Help users query customer data

## Goals

- Answer customer queries
- Provide data insights

## Tone

Professional and helpful
```

### 2. Generate Dataset

```bash
# Basic usage
python sft_dataset_generator.py users.sql objectives.md

# Custom output and sample count
python sft_dataset_generator.py users.sql objectives.md -o my_dataset.jsonl -n 500

# With custom prompts
python sft_dataset_generator.py users.sql objectives.md --prompts custom_prompts.json
```

### 3. Use with TRL

```python
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from trl import SFTConfig, SFTTrainer

# Load dataset
dataset = load_dataset('json', data_files='sft_dataset.jsonl', split='train')

# Load model
model_name = "meta-llama/Llama-2-7b-chat-hf"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Configure training
config = SFTConfig(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=4,
    dataset_text_field='messages',
    max_seq_length=2048,
)

# Train
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    args=config,
    train_dataset=dataset,
)

trainer.train()
```

## Command Line Options

```
usage: sft_dataset_generator.py [-h] [--output OUTPUT] [--num-samples NUM_SAMPLES]
                                [--api-key API_KEY] [--prompts PROMPTS]
                                [--save-prompts SAVE_PROMPTS] [--seed SEED]
                                [--temperature TEMPERATURE] [--batch-size BATCH_SIZE]
                                [--system-prompt SYSTEM_PROMPT]
                                sql_file md_file

positional arguments:
  sql_file              Path to SQL file with database schema and data
  md_file               Path to markdown file with fine-tuning specifications

optional arguments:
  -h, --help            show this help message and exit
  --output OUTPUT, -o OUTPUT
                        Output JSONL file path (default: sft_dataset.jsonl)
  --num-samples NUM_SAMPLES, -n NUM_SAMPLES
                        Number of samples to generate (default: 1000)
  --api-key API_KEY     Gemini API key (or set GEMINI_API_KEY env var)
  --prompts PROMPTS     Path to custom prompts JSON file
  --save-prompts SAVE_PROMPTS
                        Save default prompts to file and exit
  --seed SEED           Random seed for reproducibility (default: 42)
  --temperature TEMPERATURE
                        Generation temperature (default: 0.9)
  --batch-size BATCH_SIZE
                        Samples per API call (default: 10)
  --system-prompt SYSTEM_PROMPT
                        Override system prompt
```

## Prompt Customization

### Save Default Prompts

```bash
python sft_dataset_generator.py --save-prompts prompts.json
```

### Edit Prompts

Open `prompts.json` and customize any of the prompts:

```json
{
  "system_prompt": "Your custom system prompt...",
  "schema_generation": "Your prompt for schema queries...",
  "record_generation": "Your prompt for record queries...",
  "analytical_generation": "Your prompt for analytical queries...",
  "conversational_generation": "Your prompt for conversations..."
}
```

### Use Custom Prompts

```bash
python sft_dataset_generator.py users.sql objectives.md --prompts prompts.json
```

## Input File Formats

### SQL File (`users.sql`)

Supports standard SQL syntax:

```sql
-- Table creation
CREATE TABLE table_name (
    column1 TYPE CONSTRAINTS,
    column2 TYPE,
    PRIMARY KEY (column1),
    FOREIGN KEY (column2) REFERENCES other_table(id)
);

-- Data insertion
INSERT INTO table_name (column1, column2) VALUES
('value1', 'value2'),
('value3', 'value4');
```

Supported features:

- Multiple tables
- Any data types
- Primary keys
- Foreign keys
- Constraints (NOT NULL, UNIQUE, AUTO_INCREMENT)
- Multiple INSERT statements

### Markdown File (`objectives.md`)

Structure your objectives with these sections:

```markdown
## Domain

Your business domain (e.g., "E-commerce", "Healthcare")

## Business Context

Detailed description of your business and use case

## Goals

- Goal 1
- Goal 2
- Goal 3

## Target Behavior

How the assistant should behave

## FAQs

- Question 1
- Question 2

## Tone

Professional, friendly, technical, etc.

## Constraints

- Constraint 1
- Constraint 2

## System Prompt

Custom system prompt for the chat (optional)
```

All sections are optional, but more detail produces better results.

## Dataset Types

The generator creates four types of instruction-response pairs:

### 1. Schema Queries (20%)

Questions about database structure:

- "What tables are in the database?"
- "Describe the users table"
- "How are orders related to customers?"

### 2. Record Queries (35%)

Questions about specific data:

- "Show me all active users"
- "Find orders over $100"
- "What's the email for customer ID 5?"

### 3. Analytical Queries (25%)

Questions requiring analysis:

- "What are the sales trends?"
- "Which products are most popular?"
- "Analyze customer distribution by region"

### 4. Conversational (20%)

Domain-specific conversations:

- "How can you help me?"
- "What insights can you provide?"
- "Explain the business process"

## Output Format

The script generates a JSONL file where each line is a JSON object:

```json
{
  "messages": [
    {
      "role": "system",
      "content": "You are a helpful AI assistant..."
    },
    {
      "role": "user",
      "content": "What tables are in the database?"
    },
    {
      "role": "assistant",
      "content": "The database contains 4 tables:\n\n- customers (8 columns, 8 records)\n- products (7 columns, 10 records)\n..."
    }
  ]
}
```

This format is directly compatible with:

- TRL's `SFTTrainer`
- Hugging Face `datasets`
- Most fine-tuning frameworks

## Advanced Usage

### High-Quality Dataset (Lower Temperature)

```bash
python sft_dataset_generator.py users.sql objectives.md \
  --temperature 0.7 \
  --num-samples 2000
```

### Faster Generation (Larger Batches)

```bash
python sft_dataset_generator.py users.sql objectives.md \
  --batch-size 20 \
  --num-samples 500
```

### Reproducible Datasets

```bash
python sft_dataset_generator.py users.sql objectives.md \
  --seed 12345
```

### Custom System Prompt

```bash
python sft_dataset_generator.py users.sql objectives.md \
  --system-prompt "You are an expert SQL database assistant specializing in e-commerce analytics."
```

## Best Practices

### SQL File

- Include representative sample data (5-20 records per table)
- Use realistic values that reflect your domain
- Include various data types and relationships
- Add comments to explain complex schemas

### Objectives File

- Be specific about your use case and domain
- Include concrete examples in FAQs
- Define clear goals and constraints
- Specify the desired tone and style
- Add business context for better grounding

### Generation

- Start with smaller datasets (100-200) to test
- Review output quality before scaling up
- Adjust temperature based on desired creativity
- Use custom prompts for specialized domains
- Generate multiple datasets and combine the best

### Quality Control

- Review sample outputs manually
- Test with your target model
- Iterate on prompts based on results
- Monitor API costs during generation

## Troubleshooting

### "API key required" Error

```bash
export GEMINI_API_KEY="your-key-here"
# or
python script.py users.sql objectives.md --api-key "your-key-here"
```

### "No valid samples generated"

- Check your SQL file syntax
- Ensure markdown file has content
- Try increasing temperature
- Review Gemini API status

### Low Quality Output

- Add more detail to objectives.md
- Include more sample data in SQL
- Customize prompts for your domain
- Reduce batch size for more focused generation

### Rate Limiting

- The script includes automatic delays
- Reduce batch-size if hitting limits
- Check your API quota

## Cost Estimation

Gemini 2.0 Flash pricing (as of 2024):

- Input: ~$0.075 per million tokens
- Output: ~$0.30 per million tokens

Typical costs for 1,000 samples:

- Input: ~200K tokens = $0.015
- Output: ~100K tokens = $0.030
- **Total: ~$0.045 per 1,000 samples**

## Examples

See the included example files:

- `users.sql` - E-commerce database example
- `objectives.md` - E-commerce assistant objectives
- `prompts.json` - Default prompt templates

Generate example dataset:

```bash
python sft_dataset_generator.py users.sql objectives.md -n 100 -o example_dataset.jsonl
```

## Contributing

Contributions welcome! Areas for improvement:

- Support for more SQL dialects
- Additional prompt templates
- Quality metrics and validation
- Multi-language support
- Integration with other LLM APIs

## License

MIT License - feel free to use in your projects!

## Support

For issues or questions:

1. Check this README
2. Review example files
3. Test with smaller datasets first
4. Check Gemini API documentation

## Changelog

### Version 1.0

- Initial release
- Gemini 2.0 Flash integration
- External prompt configuration
- Multiple generation types
- TRL compatibility
- Production-ready error handling
