import sys
import os

project_root = os.path.join(os.path.dirname(__file__), '..')
trading_rules_dir = os.path.join(project_root, 'util')
sys.path.insert(0, project_root)
sys.path.insert(0, trading_rules_dir)
