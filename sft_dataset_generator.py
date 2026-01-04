"""
Production-ready Supervised Fine-Tuning Dataset Generator with Gemini 2.0 Flash
Generates high-quality chat datasets from SQL schemas and markdown specifications.
Compatible with TRL's SFTTrainer and Hugging Face Transformers.
"""

import re
import json
import random
import hashlib
import argparse
import time
import os
from pathlib import Path
from typing import List, Dict, Any, Tuple, Set, Optional
from dataclasses import dataclass, field
from collections import defaultdict


try:
    import sqlparse
except ImportError:
    print("Error: sqlparse not installed. Run: pip install sqlparse")
    exit(1)

try:
    import google.generativeai as genai
except ImportError:
    print("Error: google-generativeai not installed. Run: pip install google-generativeai")
    exit(1)


@dataclass
class TableSchema:
    """Represents a database table schema."""
    name: str
    columns: List[Dict[str, str]]
    records: List[Dict[str, Any]] = field(default_factory=list)
    primary_key: str = None
    foreign_keys: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class DatasetConfig:
    """Configuration for dataset generation."""
    num_samples: int = 1000
    system_prompt: str = "You are a helpful AI assistant."
    temperature: float = 0.9
    top_p: float = 0.95
    top_k: int = 40
    batch_size: int = 10
    max_retries: int = 3
    seed: int = 42
    api_key: str = None


class PromptTemplates:
    """Manages prompt templates from external file."""
    
    def __init__(self, prompts_file: Optional[Path] = None):
        self.templates = {}
        if prompts_file and prompts_file.exists():
            self._load_from_file(prompts_file)
        else:
            self._load_defaults()
    
    def _load_from_file(self, filepath: Path):
        """Load prompts from JSON file."""
        with open(filepath, 'r', encoding='utf-8') as f:
            self.templates = json.load(f)
    
    def _load_defaults(self):
        """Load default prompt templates."""
        self.templates = {
            "system_prompt": "You are an expert AI assistant specializing in generating high-quality training data for language models. Your task is to create diverse, realistic, and contextually accurate instruction-response pairs based on provided database schemas and business requirements.",
            
            "schema_generation": """Generate {num_samples} diverse instruction-response pairs about database schema information.

DATABASE SCHEMA:
{schema_info}

BUSINESS CONTEXT:
{business_context}

REQUIREMENTS:
- Create varied questions about table structures, columns, data types, relationships, and constraints
- Responses should be detailed, accurate, and reference the actual schema
- Include questions about primary keys, foreign keys, and table relationships
- Vary the complexity from simple to complex
- Use natural, conversational language
- Each instruction should be unique and not repetitive

OUTPUT FORMAT:
Return a JSON array of objects, each with:
{{"instruction": "user question here", "response": "detailed assistant response here"}}

Generate exactly {num_samples} high-quality examples.""",

            "record_generation": """Generate {num_samples} diverse instruction-response pairs about querying and retrieving specific database records.

DATABASE SCHEMA:
{schema_info}

SAMPLE RECORDS:
{sample_records}

BUSINESS CONTEXT:
{business_context}

REQUIREMENTS:
- Create varied questions about finding, filtering, and retrieving specific records
- Use actual values from the sample records provided
- Responses should reference actual data from the sample records
- Vary question complexity from simple lookups to multi-condition queries
- Use natural language, not SQL queries
- Make instructions realistic and practical

OUTPUT FORMAT:
Return a JSON array of objects, each with:
{{"instruction": "user question here", "response": "detailed assistant response here"}}

Generate exactly {num_samples} high-quality examples.""",

            "analytical_generation": """Generate {num_samples} diverse analytical instruction-response pairs about data insights and analysis.

DATABASE SCHEMA:
{schema_info}

SAMPLE RECORDS:
{sample_records}

BUSINESS CONTEXT:
{business_context}

REQUIREMENTS:
- Create varied questions requesting analysis, insights, patterns, and trends
- Include aggregations, comparisons, distributions, and statistical insights
- Responses should provide thoughtful analysis based on the data
- Ground responses in actual data while providing meaningful interpretation
- Use domain-specific terminology when appropriate

OUTPUT FORMAT:
Return a JSON array of objects, each with:
{{"instruction": "user question here", "response": "detailed assistant response here"}}

Generate exactly {num_samples} high-quality examples.""",

            "conversational_generation": """Generate {num_samples} diverse conversational instruction-response pairs based on the business domain and objectives.

BUSINESS DOMAIN:
{domain}

BUSINESS CONTEXT:
{business_context}

GOALS AND OBJECTIVES:
{goals}

FAQs (if available):
{faqs}

TONE AND STYLE:
{tone}

REQUIREMENTS:
- Create natural, conversational questions users might ask in this domain
- Include questions about the business, processes, best practices, and general help
- Responses should align with the specified tone and business objectives
- Include a mix of informational, how-to, and advisory questions
- Make conversations feel realistic and contextual to the domain

OUTPUT FORMAT:
Return a JSON array of objects, each with:
{{"instruction": "user question here", "response": "detailed assistant response here"}}

Generate exactly {num_samples} high-quality examples."""
        }
    
    def get(self, template_name: str) -> str:
        """Get a prompt template by name."""
        return self.templates.get(template_name, "")
    
    def save_to_file(self, filepath: Path):
        """Save current templates to file."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.templates, f, indent=2, ensure_ascii=False)


class SQLParser:
    """Parses SQL files and extracts schemas and data."""
    
    def __init__(self, sql_file: Path):
        self.sql_file = sql_file
        self.tables: Dict[str, TableSchema] = {}
        
    def parse(self) -> Dict[str, TableSchema]:
        """Parse SQL file and extract table schemas and data."""
        with open(self.sql_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        statements = sqlparse.split(sql_content)
        
        for stmt in statements:
            if not stmt.strip():
                continue
            parsed = sqlparse.parse(stmt)[0]
            stmt_type = parsed.get_type()
            
            if stmt_type == 'CREATE':
                self._parse_create_table(stmt)
            elif stmt_type == 'INSERT':
                self._parse_insert(stmt)
        
        return self.tables
    
    def _parse_create_table(self, stmt: str):
        """Parse CREATE TABLE statement."""
        parsed = sqlparse.parse(stmt)[0]
        
        # Extract table name
        table_name = None
        for token in parsed.tokens:
            if isinstance(token, sqlparse.sql.Identifier):
                table_name = token.get_name()
                break
            elif token.ttype is None and 'TABLE' in str(token).upper():
                parts = str(token).split()
                if len(parts) >= 2:
                    table_name = parts[-1].strip('`"[]')
        
        if not table_name:
            return
        
        # Extract column definitions
        columns = []
        primary_key = None
        foreign_keys = []
        
        paren_content = re.search(r'\((.*)\)', stmt, re.DOTALL | re.IGNORECASE)
        if paren_content:
            col_defs = paren_content.group(1)
            
            # Split by comma
            parts = []
            paren_depth = 0
            current = []
            
            for char in col_defs:
                if char == '(':
                    paren_depth += 1
                elif char == ')':
                    paren_depth -= 1
                elif char == ',' and paren_depth == 0:
                    parts.append(''.join(current).strip())
                    current = []
                    continue
                current.append(char)
            
            if current:
                parts.append(''.join(current).strip())
            
            for part in parts:
                part = part.strip()
                
                if part.upper().startswith('PRIMARY KEY'):
                    pk_match = re.search(r'PRIMARY KEY\s*\(([^)]+)\)', part, re.IGNORECASE)
                    if pk_match:
                        primary_key = pk_match.group(1).strip('`"[]')
                    continue
                
                if part.upper().startswith('FOREIGN KEY'):
                    fk_match = re.search(r'FOREIGN KEY\s*\(([^)]+)\)\s*REFERENCES\s+(\w+)\s*\(([^)]+)\)', 
                                        part, re.IGNORECASE)
                    if fk_match:
                        foreign_keys.append({
                            'column': fk_match.group(1).strip('`"[]'),
                            'ref_table': fk_match.group(2).strip('`"[]'),
                            'ref_column': fk_match.group(3).strip('`"[]')
                        })
                    continue
                
                # Parse column definition
                col_match = re.match(r'(\w+)\s+([\w\(\)]+)(?:\s+(.*))?', part, re.IGNORECASE)
                if col_match:
                    col_name = col_match.group(1).strip('`"[]')
                    col_type = col_match.group(2)
                    constraints = col_match.group(3) or ''
                    
                    col_info = {
                        'name': col_name,
                        'type': col_type,
                        'nullable': 'NOT NULL' not in constraints.upper(),
                        'unique': 'UNIQUE' in constraints.upper(),
                        'auto_increment': 'AUTO_INCREMENT' in constraints.upper() or 'AUTOINCREMENT' in constraints.upper()
                    }
                    
                    if 'PRIMARY KEY' in constraints.upper() and not primary_key:
                        primary_key = col_name
                    
                    columns.append(col_info)
        
        self.tables[table_name] = TableSchema(
            name=table_name,
            columns=columns,
            primary_key=primary_key,
            foreign_keys=foreign_keys
        )
    
    def _parse_insert(self, stmt: str):
        """Parse INSERT statement and extract records."""
        table_match = re.search(r'INSERT INTO\s+(\w+)', stmt, re.IGNORECASE)
        if not table_match:
            return
        
        table_name = table_match.group(1).strip('`"[]')
        if table_name not in self.tables:
            return
        
        col_match = re.search(r'INSERT INTO\s+\w+\s*\(([^)]+)\)', stmt, re.IGNORECASE)
        if col_match:
            columns = [c.strip().strip('`"[]') for c in col_match.group(1).split(',')]
        else:
            columns = [col['name'] for col in self.tables[table_name].columns]
        
        values_match = re.search(r'VALUES\s*(.+)', stmt, re.IGNORECASE | re.DOTALL)
        if not values_match:
            return
        
        values_str = values_match.group(1)
        
        # Extract value sets
        value_sets = []
        paren_depth = 0
        current = []
        
        for char in values_str:
            if char == '(':
                paren_depth += 1
                if paren_depth == 1:
                    continue
            elif char == ')':
                paren_depth -= 1
                if paren_depth == 0:
                    if current:
                        value_sets.append(''.join(current).strip())
                        current = []
                    continue
            
            if paren_depth > 0:
                current.append(char)
        
        # Parse each value set
        for value_set in value_sets:
            values = []
            current_val = []
            in_quote = False
            quote_char = None
            
            for i, char in enumerate(value_set):
                if char in ('"', "'") and (i == 0 or value_set[i-1] != '\\'):
                    if not in_quote:
                        in_quote = True
                        quote_char = char
                    elif char == quote_char:
                        in_quote = False
                        quote_char = None
                elif char == ',' and not in_quote:
                    values.append(''.join(current_val).strip())
                    current_val = []
                    continue
                
                current_val.append(char)
            
            if current_val:
                values.append(''.join(current_val).strip())
            
            # Create record
            record = {}
            for col, val in zip(columns, values):
                val = val.strip().strip('"\'')
                
                if val.upper() == 'NULL':
                    record[col] = None
                elif val.isdigit():
                    record[col] = int(val)
                elif re.match(r'^-?\d+\.\d+$', val):
                    record[col] = float(val)
                else:
                    record[col] = val
            
            self.tables[table_name].records.append(record)


class MarkdownParser:
    """Parses markdown specifications for fine-tuning objectives."""
    
    def __init__(self, md_file: Path):
        self.md_file = md_file
        self.spec: Dict[str, Any] = {}
        
    def parse(self) -> Dict[str, Any]:
        """Parse markdown file and extract specifications."""
        with open(self.md_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        sections = re.split(r'\n##\s+', content)
        
        for section in sections:
            if not section.strip():
                continue
            
            lines = section.split('\n', 1)
            if len(lines) == 1:
                continue
            
            title = lines[0].strip('#').strip()
            body = lines[1].strip() if len(lines) > 1 else ''
            
            key = title.lower().replace(' ', '_')
            
            # Extract bullet points or paragraphs
            if '- ' in body or '* ' in body:
                items = re.findall(r'[-*]\s+(.+)', body)
                self.spec[key] = items if items else [body]
            else:
                self.spec[key] = body
        
        return self.spec


class GeminiDatasetGenerator:
    """Generates supervised fine-tuning datasets using Gemini 2.0 Flash."""
    
    def __init__(self, 
                 tables: Dict[str, TableSchema], 
                 spec: Dict[str, Any], 
                 config: DatasetConfig,
                 prompts: PromptTemplates):
        self.tables = tables
        self.spec = spec
        self.config = config
        self.prompts = prompts
        
        # Configure Gemini
        if not config.api_key:
            raise ValueError("API key required. Set GEMINI_API_KEY environment variable or pass --api-key")
        
        genai.configure(api_key=config.api_key)
        
        self.model = genai.GenerativeModel(
            'gemini-flash-lite-latest',
            generation_config=genai.GenerationConfig(
                temperature=config.temperature,
                top_p=config.top_p,
                top_k=config.top_k,
                max_output_tokens=8192,
            )
        )
        
        random.seed(config.seed)
        self.seen_hashes: Set[str] = set()
        
        # Extract system prompt from spec
        if 'system_prompt' in spec:
            self.config.system_prompt = spec['system_prompt']
        elif 'tone' in spec:
            tone = spec['tone']
            if isinstance(tone, list):
                tone = ' '.join(tone)
            self.config.system_prompt = f"You are a helpful AI assistant. {tone}"
    
    def generate(self) -> List[Dict[str, Any]]:
        """Generate complete dataset using Gemini."""
        samples = []
        
        # Calculate distribution
        total = self.config.num_samples
        schema_samples = int(total * 0.20)
        record_samples = int(total * 0.35)
        analytical_samples = int(total * 0.25)
        conversational_samples = total - schema_samples - record_samples - analytical_samples
        
        print(f"\n  Distribution:")
        print(f"    - Schema queries: {schema_samples}")
        print(f"    - Record queries: {record_samples}")
        print(f"    - Analytical queries: {analytical_samples}")
        print(f"    - Conversational: {conversational_samples}")
        
        # Generate different types
        if schema_samples > 0:
            print(f"\n  Generating schema queries...")
            samples.extend(self._generate_with_gemini('schema_generation', schema_samples))
        
        if record_samples > 0:
            print(f"  Generating record queries...")
            samples.extend(self._generate_with_gemini('record_generation', record_samples))
        
        if analytical_samples > 0:
            print(f"  Generating analytical queries...")
            samples.extend(self._generate_with_gemini('analytical_generation', analytical_samples))
        
        if conversational_samples > 0:
            print(f"  Generating conversational samples...")
            samples.extend(self._generate_with_gemini('conversational_generation', conversational_samples))
        
        # Deduplicate and format
        print(f"\n  Deduplicating...")
        samples = self._deduplicate(samples)
        
        # Format to chat template
        formatted_samples = [self._format_to_chat(s) for s in samples]
        
        # Ensure exact count
        if len(formatted_samples) < total:
            print(f"  Generating {total - len(formatted_samples)} additional samples...")
            additional = self._generate_with_gemini('conversational_generation', total - len(formatted_samples))
            formatted_samples.extend([self._format_to_chat(s) for s in additional])
        
        random.shuffle(formatted_samples)
        return formatted_samples[:total]
    
    def _generate_with_gemini(self, generation_type: str, num_samples: int) -> List[Dict[str, str]]:
        """Generate samples using Gemini with specified prompt type."""
        all_samples = []
        batches = (num_samples + self.config.batch_size - 1) // self.config.batch_size
        
        for batch_idx in range(batches):
            batch_size = min(self.config.batch_size, num_samples - len(all_samples))
            if batch_size <= 0:
                break
            
            # Prepare context
            schema_info = self._format_schema_info()
            sample_records = self._format_sample_records()
            business_context = self._format_business_context()
            
            # Get appropriate prompt template
            prompt_template = self.prompts.get(generation_type)
            
            # Fill in template
            prompt = prompt_template.format(
                num_samples=batch_size,
                schema_info=schema_info,
                sample_records=sample_records,
                business_context=business_context,
                domain=self.spec.get('domain', 'general'),
                goals=self._format_list(self.spec.get('goals', [])),
                faqs=self._format_list(self.spec.get('faqs', [])),
                tone=self._format_list(self.spec.get('tone', []))
            )
            
            # Generate with retries
            for attempt in range(self.config.max_retries):
                try:
                    response = self.model.generate_content(prompt)
                    
                    if not response.text:
                        print(f"    Warning: Empty response on attempt {attempt + 1}")
                        time.sleep(2)
                        continue
                    
                    # Parse JSON response
                    samples = self._parse_gemini_response(response.text)
                    
                    if samples:
                        all_samples.extend(samples)
                        print(f"    Batch {batch_idx + 1}/{batches}: Generated {len(samples)} samples")
                        break
                    else:
                        print(f"    Warning: No valid samples in batch {batch_idx + 1}, attempt {attempt + 1}")
                        time.sleep(2)
                        
                except Exception as e:
                    print(f"    Error in batch {batch_idx + 1}, attempt {attempt + 1}: {str(e)}")
                    if attempt < self.config.max_retries - 1:
                        time.sleep(3)
                    else:
                        print(f"    Failed to generate batch {batch_idx + 1} after {self.config.max_retries} attempts")
            
            # Rate limiting
            time.sleep(1)
        
        return all_samples
    
    def _parse_gemini_response(self, response_text: str) -> List[Dict[str, str]]:
        """Parse Gemini's JSON response."""
        # Try to extract JSON from response
        json_match = re.search(r'\[.*\]', response_text, re.DOTALL)
        if not json_match:
            # Try with code block
            json_match = re.search(r'```json\s*(\[.*?\])\s*```', response_text, re.DOTALL)
            if json_match:
                response_text = json_match.group(1)
            else:
                return []
        else:
            response_text = json_match.group(0)
        
        try:
            data = json.loads(response_text)
            if isinstance(data, list):
                # Validate structure
                valid_samples = []
                for item in data:
                    if isinstance(item, dict) and 'instruction' in item and 'response' in item:
                        valid_samples.append({
                            'instruction': str(item['instruction']).strip(),
                            'response': str(item['response']).strip()
                        })
                return valid_samples
        except json.JSONDecodeError as e:
            print(f"    JSON parse error: {str(e)}")
        
        return []
    
    def _format_schema_info(self) -> str:
        """Format schema information for prompts."""
        info = []
        for name, table in self.tables.items():
            info.append(f"\nTable: {name}")
            info.append(f"Columns:")
            for col in table.columns:
                col_info = f"  - {col['name']} ({col['type']})"
                if not col['nullable']:
                    col_info += " NOT NULL"
                if col.get('unique'):
                    col_info += " UNIQUE"
                info.append(col_info)
            
            if table.primary_key:
                info.append(f"Primary Key: {table.primary_key}")
            
            if table.foreign_keys:
                info.append("Foreign Keys:")
                for fk in table.foreign_keys:
                    info.append(f"  - {fk['column']} -> {fk['ref_table']}.{fk['ref_column']}")
            
            info.append(f"Total Records: {len(table.records)}")
        
        return '\n'.join(info)
    
    def _format_sample_records(self, max_per_table: int = 5) -> str:
        """Format sample records for prompts."""
        info = []
        for name, table in self.tables.items():
            if not table.records:
                continue
            
            info.append(f"\nTable: {name} (showing {min(len(table.records), max_per_table)} of {len(table.records)} records)")
            for i, record in enumerate(table.records[:max_per_table], 1):
                info.append(f"  Record {i}: {json.dumps(record)}")
        
        return '\n'.join(info)
    
    def _format_business_context(self) -> str:
        """Format business context for prompts."""
        parts = []
        
        if 'business_context' in self.spec:
            context = self.spec['business_context']
            if isinstance(context, list):
                parts.extend(context)
            else:
                parts.append(str(context))
        
        if 'context' in self.spec:
            context = self.spec['context']
            if isinstance(context, list):
                parts.extend(context)
            else:
                parts.append(str(context))
        
        return '\n'.join(parts) if parts else "General purpose database assistant"
    
    def _format_list(self, items: Any) -> str:
        """Format list items for prompts."""
        if isinstance(items, list):
            return '\n'.join(f"- {item}" for item in items)
        return str(items) if items else "Not specified"
    
    def _deduplicate(self, samples: List[Dict]) -> List[Dict]:
        """Remove duplicate samples."""
        unique = []
        for sample in samples:
            content_hash = self._hash_content(sample)
            if content_hash not in self.seen_hashes:
                self.seen_hashes.add(content_hash)
                unique.append(sample)
        return unique
    
    def _hash_content(self, sample: Dict) -> str:
        """Generate hash of sample content."""
        content = json.dumps({
            'instruction': sample.get('instruction', ''),
            'response': sample.get('response', '')
        }, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()
    
    def _format_to_chat(self, sample: Dict[str, str]) -> Dict[str, Any]:
        """Format sample to chat template."""
        return {
            "messages": [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": sample['instruction']},
                {"role": "assistant", "content": sample['response']}
            ]
        }


def main():
    parser = argparse.ArgumentParser(
        description='Generate supervised fine-tuning datasets using Gemini 2.0 Flash',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Example usage:
  python sft_dataset_generator.py users.sql objectives.md --api-key YOUR_API_KEY
  python sft_dataset_generator.py users.sql objectives.md --prompts custom_prompts.json -n 500
  python sft_dataset_generator.py users.sql objectives.md --save-prompts prompts.json
        """
    )
    
    parser.add_argument('sql_file', type=Path, nargs='?',
                       help='Path to SQL file with database schema and data')
    parser.add_argument('md_file', type=Path, nargs='?',
                       help='Path to markdown file with fine-tuning specifications')
    parser.add_argument('--output', '-o', type=Path, default=Path('sft_dataset.jsonl'),
                       help='Output JSONL file path (default: sft_dataset.jsonl)')
    parser.add_argument('--num-samples', '-n', type=int, default=1000,
                       help='Number of samples to generate (default: 1000)')
    parser.add_argument('--api-key', type=str, 
                       help='Gemini API key (or set GEMINI_API_KEY env var)')
    parser.add_argument('--prompts', type=Path,
                       help='Path to custom prompts JSON file')
    parser.add_argument('--save-prompts', type=Path,
                       help='Save default prompts to specified file and exit')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility (default: 42)')
    parser.add_argument('--temperature', type=float, default=0.9,
                       help='Generation temperature (default: 0.9)')
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of samples per API call (default: 10)')
    parser.add_argument('--system-prompt', type=str,
                       help='Override system prompt')
    
    args = parser.parse_args()
    
    # Handle save prompts
    if args.save_prompts:
        prompts = PromptTemplates()
        prompts.save_to_file(args.save_prompts)
        print(f"✓ Saved default prompts to: {args.save_prompts}")
        return 0
    
    # Validate required arguments
    if not args.sql_file or not args.md_file:
        parser.print_help()
        print("\nError: sql_file and md_file are required unless using --save-prompts")
        return 1
    
    # Get API key
    api_key = args.api_key or os.environ.get('GEMINI_API_KEY')
    if not api_key:
        print("Error: Gemini API key required. Use --api-key or set GEMINI_API_KEY environment variable")
        return 1
    
    # Validate inputs
    if not args.sql_file.exists():
        print(f"Error: SQL file not found: {args.sql_file}")
        return 1
    
    if not args.md_file.exists():
        print(f"Error: Markdown file not found: {args.md_file}")
        return 1
    
    print("=" * 80)
    print("SFT Dataset Generator with Gemini 2.0 Flash")
    print("=" * 80)
    
    # Load prompts
    print(f"\n[1/5] Loading prompt templates...")
    prompts = PromptTemplates(args.prompts)
    if args.prompts:
        print(f"  ✓ Loaded custom prompts from: {args.prompts}")
    else:
        print(f"  ✓ Using default prompt templates")
    
    # Parse SQL file
    print(f"\n[2/5] Parsing SQL file: {args.sql_file}")
    sql_parser = SQLParser(args.sql_file)
    tables = sql_parser.parse()
    print(f"  ✓ Found {len(tables)} table(s)")
    
    total_records = sum(len(t.records) for t in tables.values())
    print(f"  ✓ Loaded {total_records} record(s)")
    
    for name, table in tables.items():
        print(f"    - {name}: {len(table.columns)} columns, {len(table.records)} records")
    
    # Parse markdown specification
    print(f"\n[3/5] Parsing markdown specification: {args.md_file}")
    md_parser = MarkdownParser(args.md_file)
    spec = md_parser.parse()
    print(f"  ✓ Loaded specification with {len(spec)} section(s)")
    
    for key in list(spec.keys())[:5]:
        print(f"    - {key}")
    if len(spec) > 5:
        print(f"    ... and {len(spec) - 5} more")
    
    # Configure dataset generation
    config = DatasetConfig(
        num_samples=args.num_samples,
        seed=args.seed,
        temperature=args.temperature,
        batch_size=args.batch_size,
        api_key=api_key
    )
    
    if args.system_prompt:
        config.system_prompt = args.system_prompt
    
    # Generate dataset
    print(f"\n[4/5] Generating {args.num_samples} samples with Gemini 2.0 Flash...")
    print(f"  Model: gemini-2.0-flash-exp")
    print(f"  Temperature: {config.temperature}")
    print(f"  Batch size: {config.batch_size}")
    
    try:
        generator = GeminiDatasetGenerator(tables, spec, config, prompts)
        dataset = generator.generate()
    except Exception as e:
        print(f"\n✗ Error during generation: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    
    print(f"\n  ✓ Generated {len(dataset)} unique samples")
    
    # Calculate statistics
    avg_user_len = sum(len(s['messages'][1]['content']) for s in dataset) / len(dataset)
    avg_assistant_len = sum(len(s['messages'][2]['content']) for s in dataset) / len(dataset)
    print(f"  ✓ Average user message length: {avg_user_len:.0f} characters")
    print(f"  ✓ Average assistant message length: {avg_assistant_len:.0f} characters")
    
    # Save dataset
    print(f"\n[5/5] Saving dataset to: {args.output}")
    
    with open(args.output, 'w', encoding='utf-8') as f:
        for sample in dataset:
            f.write(json.dumps(sample, ensure_ascii=False) + '\n')
    
    print(f"  ✓ Saved {len(dataset)} samples")
    
    # Print examples
    print("\n" + "=" * 80)
    print("Example samples:")
    print("=" * 80)
    
    for i, example in enumerate(dataset[:2], 1):
        print(f"\n--- Example {i} ---")
        print(f"\nSystem: {example['messages'][0]['content'][:100]}...")
        print(f"\nUser: {example['messages'][1]['content']}")
        print(f"\nAssistant: {example['messages'][2]['content'][:200]}...")
    
    print("\n" + "=" * 80)
    print("✓ Dataset generation complete!")
    print("=" * 80)
    
    print(f"""
To use with TRL's SFTTrainer:

from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM
from trl import SFTConfig, SFTTrainer

# Load your model and tokenizer
model_name = "your-model-name"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name)

# Load dataset
dataset = load_dataset('json', data_files='{args.output}', split='train')

# Configure training
config = SFTConfig(
    output_dir='./results',
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-5,
    warmup_steps=100,
    logging_steps=10,
    save_steps=100,
    dataset_text_field='messages',
    max_seq_length=2048,
)

# Initialize trainer
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    args=config,
    train_dataset=dataset,
)

# Start training
trainer.train()
""")
    
    return 0


if __name__ == '__main__':
    exit(main())