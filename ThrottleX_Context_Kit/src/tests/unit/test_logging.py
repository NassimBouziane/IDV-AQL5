"""Unit tests for logging configuration."""

from unittest.mock import MagicMock, patch

from throttlex.logging import setup_logging


class TestLogging:
    """Tests for logging setup."""

    @patch("throttlex.logging.get_settings")
    @patch("throttlex.logging.structlog")
    def test_setup_logging_json(self, mock_structlog, mock_get_settings):
        """Test logging setup with JSON format."""
        mock_settings = MagicMock()
        mock_settings.log_format = "json"
        mock_settings.log_level = "INFO"
        mock_get_settings.return_value = mock_settings

        setup_logging()

        mock_structlog.configure.assert_called_once()

    @patch("throttlex.logging.get_settings")
    @patch("throttlex.logging.structlog")
    def test_setup_logging_console(self, mock_structlog, mock_get_settings):
        """Test logging setup with console format."""
        mock_settings = MagicMock()
        mock_settings.log_format = "console"
        mock_settings.log_level = "DEBUG"
        mock_get_settings.return_value = mock_settings

        setup_logging()

        mock_structlog.configure.assert_called_once()
