"""
Unit tests for configuration management system.
"""

import os
import tempfile
from pathlib import Path
from unittest import TestCase
from configparser import ConfigParser
from datetime import datetime

from app.config.settings import ConfigurationManager, ConfigurationError

class TestConfigurationManager(TestCase):
    """Test cases for ConfigurationManager."""
    
    def setUp(self):
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "test_config.ini"
        self.default_config = {
            'logging': {
                'level': 'INFO',
                'file': 'bot.log'
            },
            'mt5': {
                'terminal_path': 'C:\\Program Files\\MetaTrader 5\\terminal64.exe',
                'server': 'demo.mt5.com',
                'login': '12345',
                'password': 'password'
            },
            'database': {
                'host': 'localhost',
                'port': '5432',
                'name': 'haruquant',
                'user': 'postgres',
                'password': 'postgres'
            }
        }
        self.manager = ConfigurationManager(
            config_path=str(self.config_path),
            default_config=self.default_config
        )
        
    def tearDown(self):
        """Clean up test environment."""
        self.temp_dir.cleanup()
        
    def test_initialization(self):
        """Test ConfigurationManager initialization."""
        self.assertEqual(self.manager.config_path, self.config_path)
        self.assertEqual(self.manager.env_prefix, "HARUQUANT_")
        self.assertEqual(self.manager.default_config, self.default_config)
        
    def test_load_default_config(self):
        """Test loading default configuration."""
        self.manager.load()
        self.assertEqual(self.manager.to_dict(), self.default_config)
        
    def test_load_ini_config(self):
        """Test loading configuration from INI file."""
        # Create test INI file
        config = ConfigParser()
        config['logging'] = {'level': 'DEBUG'}
        config['mt5'] = {'server': 'test.mt5.com'}
        
        with open(self.config_path, 'w') as f:
            config.write(f)
            
        self.manager.load()
        
        # Check that INI values override defaults
        self.assertEqual(self.manager.get('logging', 'level'), 'DEBUG')
        self.assertEqual(self.manager.get('mt5', 'server'), 'test.mt5.com')
        
    def test_load_env_config(self):
        """Test loading configuration from environment variables."""
        # Set test environment variables
        os.environ['HARUQUANT_LOGGING_LEVEL'] = 'ERROR'
        os.environ['HARUQUANT_MT5_SERVER'] = 'env.mt5.com'
        
        self.manager.load()
        
        # Check that env values override defaults
        self.assertEqual(self.manager.get('logging', 'level'), 'ERROR')
        self.assertEqual(self.manager.get('mt5', 'server'), 'env.mt5.com')
        
        # Clean up
        del os.environ['HARUQUANT_LOGGING_LEVEL']
        del os.environ['HARUQUANT_MT5_SERVER']
        
    def test_validation(self):
        """Test configuration validation."""
        # Test missing required section
        invalid_config = self.default_config.copy()
        del invalid_config['mt5']
        
        with self.assertRaises(ConfigurationError):
            self.manager.from_dict(invalid_config)
            
        # Test missing required key
        invalid_config = self.default_config.copy()
        del invalid_config['mt5']['server']
        
        with self.assertRaises(ConfigurationError):
            self.manager.from_dict(invalid_config)
            
    def test_get_set(self):
        """Test getting and setting configuration values."""
        self.manager.load()
        
        # Test get with type hinting
        self.assertEqual(self.manager.get('mt5', 'login', type_hint=int), 12345)
        
        # Test get with default
        self.assertEqual(self.manager.get('test', 'key', default='default'), 'default')
        
        # Test set
        self.manager.set('test', 'key', 'value')
        self.assertEqual(self.manager.get('test', 'key'), 'value')
        
    def test_save(self):
        """Test saving configuration to file."""
        self.manager.load()
        self.manager.save()
        
        # Verify saved file
        config = ConfigParser()
        config.read(self.config_path)
        
        self.assertTrue(config.has_section('logging'))
        self.assertTrue(config.has_section('mt5'))
        self.assertTrue(config.has_section('database'))
        
    def test_section_operations(self):
        """Test section-level operations."""
        self.manager.load()
        
        # Test get_section
        logging_section = self.manager.get_section('logging')
        self.assertEqual(logging_section, self.default_config['logging'])
        
        # Test update_section
        new_logging = {'level': 'DEBUG', 'file': 'new.log'}
        self.manager.update_section('logging', new_logging)
        self.assertEqual(self.manager.get_section('logging'), new_logging)
        
    def test_version_and_timestamp(self):
        """Test version and timestamp functionality."""
        self.manager.load()
        
        self.assertEqual(self.manager.get_version(), "1.0.0")
        self.assertIsInstance(self.manager.get_last_loaded(), datetime) 