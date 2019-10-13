# qfx_fixer
Script to fix transactions in QFX file downloaded from Capital One

## Requirements
- python 3.7+
- lxml 4.4.1+
- ofxtools 0.8.16+

## Usage
1. Download transactions from Captial One in QFX format
1. Clone repo:
   ```
   git clone https://github.com/pymonger/qfx_fixer.git
   cd qfx_fixer
   ```
1. Convert the downloaded QFX file:
   ```
   ./add_name_from_memo.py <input_qfx_file> <output_qfx_file>
   ```
   For example:
   ```
   ./add_name_from_memo.py 2019-10-04_transaction_download.qfx fixed.qfx
   ```
1. Import in Microsoft Money
