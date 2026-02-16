# qfx_fixer

Script to fix transactions in QFX files downloaded from Capital One for import into Microsoft Money.

Capital One QFX files lack the required `NAME` field for transactions. This script extracts names from the `MEMO` field using pattern matching.

## Requirements

- Python 3.10+
- lxml 4.4.1+
- ofxtools 0.8.16+

## Installation

```bash
git clone https://github.com/pymonger/qfx_fixer.git
cd qfx_fixer
pip install -r requirements.txt
```

## Usage

```bash
./add_name_from_memo.py <input_qfx_file> <output_qfx_file>
```

For example:

```bash
./add_name_from_memo.py 2019-10-04_transaction_download.qfx fixed.qfx
```

Use `--skip-unknown` to skip unrecognized transactions instead of crashing:

```bash
./add_name_from_memo.py --skip-unknown input.qfx output.qfx
```

Then import the output file into Microsoft Money.

## Supported Transaction Types

The following memo patterns are recognized:

| Pattern | Name Extraction |
|---------|----------------|
| `Withdrawal from <payee>` | Payee name |
| `Debit Card Purchase - <payee>` | Payee name |
| `Deposit from <payee>` | Payee name |
| `ATM Withdrawal - <location>` | Location |
| `Digital Card Purchase - <payee>` | Payee name |
| `Miscellaneous <description>` | Description |
| `Monthly Interest Paid` | "Capital One" |
| `Check #NNN Cashed` | Full memo text |
| `Check Deposit (Mobile)` | Full memo text |
| `Prenote` | Full memo text |
| `360 Checking` | Full memo text |
| `Zelle money sent to / received from ...` | Full memo text |
| `Withdrawal to` | Full memo text |
| `Checkbook Order` | Full memo text |
| `Deposit from MONEY` | Full memo text |
| `Deposit from Savings` | Full memo text |

Names are truncated to 31 characters (OFX field limit).

## Adding New Transaction Patterns

Edit the `TRANSACTION_RULES` list in `add_name_from_memo.py`:

```python
TRANSACTION_RULES = [
    (re.compile(r'Your Pattern', re.I), 0),  # use group(0) = full match
    # ... existing rules ...
]
```

The second element is either:
- `0` — use the full regex match as the name
- `1` (or higher) — use a capture group as the name
- A string — use a static name (e.g., `"Capital One"`)

## Running Tests

```bash
pip install pytest
pytest test_add_name_from_memo.py -v
```
