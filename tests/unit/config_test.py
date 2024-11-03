import os
import unittest
from unittest.mock import patch, mock_open
from src.config import Env, RuntimeConfig


class TestEnv(unittest.TestCase):
    @patch(
        "src.config.load_dotenv"
    )  # Mock load_dotenv to prevent loading the actual .env file
    @patch.dict(
        os.environ, {"DUNE_API_KEY": "test_key", "DB_URL": "postgres://localhost/test"}
    )
    def test_load_env_success(self, mock_load_dotenv):
        env = Env.load()
        self.assertEqual(env.dune_api_key, "test_key")
        self.assertEqual(env.db_url, "postgres://localhost/test")

    @patch(
        "src.config.load_dotenv"
    )  # Mock load_dotenv to prevent loading the actual .env file
    @patch.dict(os.environ, {}, clear=True)
    def test_load_env_missing_dune_api_key(self, mock_load_dotenv):
        with self.assertRaises(RuntimeError) as context:
            Env.load()
        self.assertEqual(
            str(context.exception), "DUNE_API_KEY environment variable must be set!"
        )

    @patch(
        "src.config.load_dotenv"
    )  # Mock load_dotenv to prevent loading the actual .env file
    @patch.dict(os.environ, {"DUNE_API_KEY": "test_key"}, clear=True)
    def test_load_env_missing_db_url(self, mock_load_dotenv):
        with self.assertRaises(RuntimeError) as context:
            Env.load()
        self.assertEqual(
            str(context.exception), "DB_URL environment variable must be set!"
        )


class TestRuntimeConfig(unittest.TestCase):
    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=b"""
        [[jobs]]
        source = "dune"
        destination = "postgres"
        query_id = 123
        table_name = "test_table"
        poll_frequency = 5
        query_engine = "medium"
    """,
    )
    def test_load_from_toml_success(self, mock_file):
        config = RuntimeConfig.load_from_toml("config.toml")
        self.assertEqual(len(config.dune_to_local_jobs), 1)
        job = config.dune_to_local_jobs[0]
        self.assertEqual(job.query_id, 123)
        self.assertEqual(job.table_name, "test_table")
        self.assertEqual(job.poll_frequency, 5)
        self.assertEqual(job.query_engine, "medium")

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=b"""
        [[jobs]]
        source = "dune"
        destination = "postgres"
        query_id = 123
        table_name = "test_table"
        poll_frequency = 5
        query_engine = "invalid"
    """,
    )
    def test_load_from_toml_invalid_query_engine(self, mock_file):
        with self.assertRaises(ValueError) as context:
            RuntimeConfig.load_from_toml("config.toml")
        self.assertEqual(
            str(context.exception), "query_engine must be either 'medium' or 'large'."
        )

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=b"""
        [[jobs]]
        source = "postgres"
        destination = "postgres"
        query_id = 123
        table_name = "test_table"
        poll_frequency = 5
        query_engine = "invalid"
    """,
    )
    def test_load_from_toml_invalid_source_dest_combo(self, mock_file):
        with self.assertRaises(ValueError) as context:
            RuntimeConfig.load_from_toml("config.toml")
        self.assertEqual(
            str(context.exception),
            "Invalid source/destination combination: DataSource.POSTGRES -> DataSource.POSTGRES",
        )

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=b"""
        [[jobs]]
        source = "dune"
        destination = "postgres"
        table_name = "test_table"
        query_id = 123
    """,
    )
    def test_load_from_toml_missing_values(self, mock_file):
        config = RuntimeConfig.load_from_toml("config.toml")
        self.assertEqual(len(config.dune_to_local_jobs), 1)
        job = config.dune_to_local_jobs[0]
        self.assertEqual(job.query_id, 123)
        self.assertEqual(job.table_name, "test_table")  # Default table name
        self.assertEqual(job.poll_frequency, 1)  # Default poll frequency
        self.assertEqual(job.query_engine, "medium")  # Default query engine

    @patch(
        "builtins.open",
        new_callable=mock_open,
        read_data=b"""

        [[jobs]]
        source = "postgres"
        destination = "dune"
        table_name = "test_table"
        query_string = "SELECT * FROM test_table"
    """,
    )
    def test_load_from_toml_for_local_to_dune(self, mock_file):
        config = RuntimeConfig.load_from_toml("config.toml")
        self.assertEqual(len(config.dune_to_local_jobs), 0)
        self.assertEqual(len(config.local_to_dune_jobs), 1)
        job = config.local_to_dune_jobs[0]
