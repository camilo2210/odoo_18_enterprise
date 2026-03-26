# -*- coding: utf-8 -*-
"""
SFTPService: Encapsulates all paramiko SFTP operations.
Pure Python class — no Odoo ORM dependency.
"""
import io
import stat
import logging

_logger = logging.getLogger(__name__)


class SFTPService:
    """
    Thin wrapper around paramiko for SFTP file operations.
    Supports password and private key (RSA/Ed25519/ECDSA/DSS) authentication.
    """

    def __init__(self, config):
        """
        :param config: sftp.bank.config recordset (provides connection params)
        """
        self._config = config
        self._transport = None
        self._sftp = None

    # ── Connection ────────────────────────────────────────────────────────
    def connect(self):
        """Establish SFTP connection. Raises ConnectionError on failure."""
        try:
            import paramiko
        except ImportError as exc:
            raise ImportError(
                'paramiko is not installed. Run: pip install paramiko'
            ) from exc

        try:
            self._transport = paramiko.Transport(
                (self._config.sftp_host, int(self._config.sftp_port))
            )
            # Harden: disable weak legacy algorithms
            self._transport.disabled_algorithms = {
                'pubkeys': ['rsa-sha2-256', 'rsa-sha2-512'],  # keep only modern if needed
            }

            if self._config.auth_method == 'password':
                self._transport.connect(
                    username=self._config.sftp_user,
                    password=self._config.sftp_password,
                )
            else:
                pkey = self._load_private_key()
                self._transport.connect(
                    username=self._config.sftp_user,
                    pkey=pkey,
                )

            self._sftp = paramiko.SFTPClient.from_transport(self._transport)
            _logger.info(
                'SFTPService: Connected to %s:%s',
                self._config.sftp_host, self._config.sftp_port,
            )

        except Exception as exc:
            self.close()
            raise ConnectionError(
                f'Cannot connect to {self._config.sftp_host}:{self._config.sftp_port}: {exc}'
            ) from exc

    def _load_private_key(self):
        """
        Auto-detect and load private key from config content.
        Tries RSA, Ed25519, ECDSA, DSS in order.
        """
        import paramiko

        key_content = (self._config.sftp_private_key or '').strip()
        passphrase = self._config.sftp_key_passphrase or None

        key_classes = [
            paramiko.RSAKey,
            paramiko.Ed25519Key,
            paramiko.ECDSAKey,
            paramiko.DSSKey,
        ]
        last_error = None
        for key_class in key_classes:
            try:
                key_file = io.StringIO(key_content)
                return key_class.from_private_key(key_file, password=passphrase)
            except paramiko.SSHException as exc:
                last_error = exc
                continue

        raise ValueError(
            f'Could not load private key — unsupported type or wrong passphrase. '
            f'Last error: {last_error}'
        )

    # ── File Operations ───────────────────────────────────────────────────
    def list_files(self, remote_path):
        """
        List filenames (not subdirectories) in remote_path.
        Returns a list of filename strings (not full paths).
        """
        self._assert_connected()
        try:
            entries = self._sftp.listdir_attr(remote_path)
            return [
                entry.filename
                for entry in entries
                if not stat.S_ISDIR(entry.st_mode or 0)
            ]
        except IOError as exc:
            raise FileNotFoundError(
                f'Cannot list remote directory "{remote_path}": {exc}'
            ) from exc

    def read_file(self, remote_path):
        """
        Download a remote file and return its raw bytes content.
        Uses chunked transfer to avoid memory issues with large files.
        """
        self._assert_connected()
        buffer = io.BytesIO()
        try:
            with self._sftp.open(remote_path, 'rb') as remote_file:
                remote_file.prefetch()  # paramiko optimization for sequential reads
                while True:
                    chunk = remote_file.read(65536)  # 64 KB chunks
                    if not chunk:
                        break
                    buffer.write(chunk)
            return buffer.getvalue()
        except IOError as exc:
            raise IOError(f'Cannot read remote file "{remote_path}": {exc}') from exc

    def move_file(self, source_path, dest_path):
        """
        Move/rename a file on the SFTP server.
        Creates the destination directory if it does not exist.
        """
        self._assert_connected()
        dest_dir = dest_path.rsplit('/', 1)[0]
        self._ensure_remote_dir(dest_dir)
        try:
            self._sftp.rename(source_path, dest_path)
        except IOError as exc:
            raise IOError(
                f'Cannot move "{source_path}" → "{dest_path}": {exc}'
            ) from exc

    def _ensure_remote_dir(self, remote_path):
        """Create remote directory recursively if it does not exist."""
        try:
            self._sftp.stat(remote_path)
        except IOError:
            # Directory does not exist — create it
            parent = remote_path.rsplit('/', 1)[0]
            if parent and parent != remote_path:
                self._ensure_remote_dir(parent)
            try:
                self._sftp.mkdir(remote_path)
                _logger.info('SFTPService: Created remote directory "%s"', remote_path)
            except IOError:
                pass  # Already exists (race condition), safe to ignore

    # ── Lifecycle ─────────────────────────────────────────────────────────
    def close(self):
        """Gracefully close SFTP client and transport."""
        try:
            if self._sftp:
                self._sftp.close()
        except Exception:
            pass
        try:
            if self._transport and self._transport.is_active():
                self._transport.close()
        except Exception:
            pass
        finally:
            self._sftp = None
            self._transport = None
            _logger.debug('SFTPService: Connection closed.')

    def _assert_connected(self):
        if not self._sftp or not self._transport or not self._transport.is_active():
            raise RuntimeError(
                'SFTPService: Not connected. Call connect() before any file operation.'
            )

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False  # Do not suppress exceptions
