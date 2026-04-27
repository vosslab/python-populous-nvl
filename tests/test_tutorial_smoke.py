"""Smoke tests for tutorial content (M8)."""

import os

import yaml


def test_tutorial_01_yaml_loads():
	"""tutorial_01.yaml parses and references a real scenario."""
	repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
	tutorial_path = os.path.join(repo_root, 'data', 'tutorial', 'tutorial_01.yaml')
	with open(tutorial_path) as fh:
		data = yaml.safe_load(fh)
	assert data['format_version'] == 1
	assert isinstance(data['steps'], list)
	assert len(data['steps']) >= 1
	scenario_name = data['scenario']
	scenario_path = os.path.join(repo_root, 'data', 'scenarios', f'{scenario_name}.yaml')
	assert os.path.exists(scenario_path)
