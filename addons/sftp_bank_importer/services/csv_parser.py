# -*- coding: utf-8 -*-
"""
CSVParser: Parses raw CSV bytes into normalized row dicts.
Pure Python class — no Odoo ORM dependency.
"""
import csv
import io
import logging
from datetime import datetime

_logger = logging.getLogger(__name__)


class CSVParser:
    """
    Converts CSV file content (bytes) into a list of normalized dicts
    ready to be mapped to account.bank.statement.line values.

    Each output row has keys: date, reference, amount, partner
    """

    def __init__(self, config):
        """
        :param config: sftp.bank.config recordset
        """
        self._config = config

    def parse(self, raw_bytes):
        """
        Main entry point. Decode and parse CSV bytes.

        :param raw_bytes: bytes — raw file content
        :returns: list of dicts with normalized values
        :raises ValueError: on structural CSV errors
        """
        text = self._decode(raw_bytes)
        reader = self._build_reader(text)

        if self._config.csv_has_header:
            self._validate_headers(reader.fieldnames)

        rows = []
        for row_num, raw_row in enumerate(reader, start=2):
            parsed = self._parse_row(raw_row, row_num)
            if parsed is not None:
                rows.append(parsed)

        _logger.debug('CSVParser: Parsed %d valid rows from CSV.', len(rows))
        return rows

    # ── Internals ─────────────────────────────────────────────────────────
    def _decode(self, raw_bytes):
        """Decode bytes to string using configured encoding."""
        encoding = (self._config.csv_encoding or 'utf-8').strip()
        try:
            return raw_bytes.decode(encoding)
        except (UnicodeDecodeError, LookupError) as exc:
            raise ValueError(
                f'Cannot decode file with encoding "{encoding}": {exc}. '
                f'Try latin-1 or cp1252 for legacy bank exports.'
            ) from exc

    def _build_reader(self, text):
        """Create a csv.DictReader from the decoded text."""
        separator = (self._config.csv_separator or ',')
        # Handle BOM character from Excel/Windows exports
        if text.startswith('\ufeff'):
            text = text.lstrip('\ufeff')
        return csv.DictReader(io.StringIO(text), delimiter=separator)

    def _validate_headers(self, fieldnames):
        """Ensure all configured column names exist in the CSV header."""
        if fieldnames is None:
            raise ValueError('CSV file is empty or has no header row.')

        # Strip BOM and whitespace from headers
        clean = [h.strip().lstrip('\ufeff') for h in fieldnames]

        required = {
            self._config.col_date,
            self._config.col_amount,
            self._config.col_reference,
        }
        missing = required - set(clean)
        if missing:
            raise ValueError(
                f'CSV is missing required columns: {sorted(missing)}. '
                f'Available columns: {clean}'
            )

    def _parse_row(self, raw_row, row_num):
        """
        Parse and normalize a single DictReader row.
        Returns None to skip silently (missing required field or parse error).
        """
        try:
            # Strip whitespace from all values
            row = {k: (v or '').strip() for k, v in raw_row.items() if k}

            date_str = row.get(self._config.col_date, '')
            reference = row.get(self._config.col_reference, '')
            amount_str = row.get(self._config.col_amount, '')
            partner = row.get(self._config.col_partner or '', '') if self._config.col_partner else ''

            # Skip rows missing critical fields
            if not date_str:
                _logger.debug('Row %d: missing date value, skipping.', row_num)
                return None
            if not amount_str:
                _logger.debug('Row %d: missing amount value, skipping.', row_num)
                return None

            return {
                'date': self._parse_date(date_str, row_num),
                'reference': reference,
                'amount': self._parse_amount(amount_str, row_num),
                'partner': partner,
            }

        except (ValueError, KeyError, TypeError) as exc:
            _logger.warning(
                'CSVParser: Row %d — parse error (%s), row content: %s',
                row_num, exc, dict(raw_row),
            )
            return None

    def _parse_date(self, date_str, row_num):
        """Parse date string using the configured strptime format."""
        fmt = self._config.date_format or '%d/%m/%Y'
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError as exc:
            raise ValueError(
                f'Row {row_num}: date "{date_str}" does not match format "{fmt}".'
            ) from exc

    def _parse_amount(self, amount_str, row_num):
        """
        Parse amount string handling both decimal separator conventions.
        Supports negative amounts with leading minus or parentheses notation.
        """
        cleaned = amount_str.strip()

        # Parentheses notation → negative
        negative = False
        if cleaned.startswith('(') and cleaned.endswith(')'):
            negative = True
            cleaned = cleaned[1:-1]

        dec_sep = self._config.decimal_separator  # '.' or ','

        if dec_sep == ',':
            # European: dots are thousands separators, comma is decimal
            cleaned = cleaned.replace('.', '').replace(',', '.')
        else:
            # US/Anglo: commas are thousands separators, dot is decimal
            cleaned = cleaned.replace(',', '')

        # Remove remaining non-numeric chars except minus and dot
        cleaned = cleaned.replace(' ', '').replace('\xa0', '')

        try:
            value = float(cleaned)
            return -abs(value) if negative else value
        except ValueError as exc:
            raise ValueError(
                f'Row {row_num}: cannot parse amount "{amount_str}" → "{cleaned}".'
            ) from exc