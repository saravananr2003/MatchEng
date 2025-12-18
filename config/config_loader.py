
  import json
  import os
  from typing import Dict, Any
  
  
  class Config:
      """Unified configuration class that loads settings from JSON files"""
  
      _instance = None
      _settings = None
      _column_config = None
  
      def __new__(cls):
         if cls._instance is None:
            cls._instance = super(Config, cls).__new__(cls)
            cls._instance._load_settings()
         return cls._instance
  
      def _load_settings(self):
         """Load settings from JSON file"""
         config_dir = os.path.dirname(os.path.abspath(__file__))
         settings_file = os.path.join(config_dir, 'settings.json')
  
         with open(settings_file, 'r') as f:
            self._settings = json.load(f)
  
      def get(self, key_path: str, default: Any = None) -> Any:
         """
         Get configuration value using dot notation
         Example: config.get('matching.company_name_threshold')
         """
         keys = key_path.split('.')
         value = self._settings
  
         for key in keys:
            if isinstance(value, dict) and key in value:
               value = value[key]
            else:
               return default
  
         return value
  
      def get_section(self, section: str) -> Dict:
         """Get entire configuration section"""
         return self._settings.get(section, {})
  
      @property
      def app(self):
         """App configuration"""
         return self.get_section('app')
  
      @property
      def matching(self):
         """Matching thresholds configuration"""
         return self.get_section('matching')
  
      @property
      def ml(self):
         """ML configuration"""
         return self.get_section('ml')
  
      @property
      def scoring(self):
         """Scoring weights configuration"""
         return self.get_section('scoring')
  
      @property
      def logging(self):
         """Logging configuration"""
         return self.get_section('logging')
  
      @property
      def dedup(self):
         """Dedup configuration"""
         return self.get_section('dedup')
  
  
  # Global config instance
  _config = None
  
  
  def get_config() -> Config:
      """Get or create the global configuration instance"""
      global _config
      if _config is None:
         _config = Config()
      return _config