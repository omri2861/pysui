#    Copyright Frank V. Castellucci
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#        http://www.apache.org/licenses/LICENSE-2.0
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# -*- coding: utf-8 -*-


"""Default Sui Configuration."""


import os
from io import TextIOWrapper

from pathlib import Path
import json
import yaml
from deprecated.sphinx import deprecated, versionadded
from pysui.abstracts import ClientConfiguration, SignatureScheme, KeyPair
from pysui.sui.sui_constants import (
    PYSUI_EXEC_ENV,
    PYSUI_CLIENT_CONFIG_ENV,
    DEFAULT_SUI_BINARY_PATH,
    DEFAULT_DEVNET_PATH_STRING,
    DEVNET_FAUCET_URL,
    DEVNET_SOCKET_URL,
    LOCALNET_ENVIRONMENT_KEY,
    LOCALNET_FAUCET_URL,
    LOCALNET_SOCKET_URL,
    TESTNET_ENVIRONMENT_KEY,
    TESTNET_FAUCET_URL,
    TESTNET_SOCKET_URL,
)
from pysui.sui.sui_crypto import SuiAddress, create_new_address, load_keys_and_addresses
from pysui.sui.sui_excepts import (
    SuiConfigFileError,
    SuiFileNotFound,
)
from pysui.sui.sui_utils import sui_base_get_config


@versionadded(version="0.16.1", reason="Support for sui-base as well as sharing with signing and publishing")
def _set_env_vars(client_config_path: Path, sui_exec_path: Path):
    """_set_env_vars Sets runtime paths to environment variables.

    The most important will be the binary execution for compiling move packages and
    performing MultiSig signing.

    :param client_config_path: _description_
    :type client_config_path: Path
    :param sui_exec_path: _description_
    :type sui_exec_path: Path
    """
    os.environ[PYSUI_CLIENT_CONFIG_ENV] = str(client_config_path)
    os.environ[PYSUI_EXEC_ENV] = str(sui_exec_path)


# pylint:disable=too-many-instance-attributes,attribute-defined-outside-init,too-many-arguments,unnecessary-dunder-call
class SuiConfig(ClientConfiguration):
    """Sui default configuration class."""

    def _old_init(self, config_path: str, env: str, active_address: str, keystore_file: str, current_url: str) -> None:
        """__init__ SuiConfig initialization.

        :param config_path: Fully qualified path to client.yaml configuration to use.
        :type config_path: str
        :param env: The active environment name (e.g. devnet, localnet)
        :type env: str
        :param active_address: Which address to set as active-address
        :type active_address: str
        :param keystore_file: Fully qualifed path to keystore file
        :type keystore_file: str
        :param current_url: URL of SUI gateway to use (e.g. https://fullnode.devnet.sui.io:443)
        :type current_url: str
        :raises SuiInvalidKeystringLength: If, when ingesting keys, pre 0.21.0 keystring found
        :raises SuiNoKeyPairs: If keystore file is empty
        :raises SuiKeystoreFileError: If exception occured during keystore file read
        :raises SuiKeystoreAddressError: If JSON error reading keystring array from keystore file
        :raises SuiFileNotFound: If path to keystore file does not exist
        """
        super().__init__(config_path, keystore_file)
        self._active_address = SuiAddress(active_address)
        self._current_url = current_url
        self._current_env = env
        # Add for foward capability
        _set_env_vars(config_path, Path(os.path.expanduser(DEFAULT_SUI_BINARY_PATH)))
        if env == LOCALNET_ENVIRONMENT_KEY:
            self._faucet_url = LOCALNET_FAUCET_URL
            self._socket_url = LOCALNET_SOCKET_URL
            self._local_running = True
        elif env == TESTNET_ENVIRONMENT_KEY:
            self._faucet_url = TESTNET_FAUCET_URL
            self._socket_url = TESTNET_SOCKET_URL
            self._local_running = False
        else:
            self._faucet_url = DEVNET_FAUCET_URL
            self._socket_url = DEVNET_SOCKET_URL
            self._local_running = False
        self._keypairs, self._addresses, self._address_keypair = load_keys_and_addresses(keystore_file)

    def _initiate(self, active_address: str, rpc_url: str, environment: str) -> None:
        """."""
        self._active_address = SuiAddress(active_address)
        self._current_url = rpc_url
        self._current_env = environment
        match self._current_env:
            case "devnet":
                self._faucet_url = DEVNET_FAUCET_URL
                self._socket_url = DEVNET_SOCKET_URL
            case "testnet":
                self._faucet_url = TESTNET_FAUCET_URL
                self._socket_url = TESTNET_SOCKET_URL
            case "localnet":
                self._faucet_url = LOCALNET_FAUCET_URL
                self._socket_url = LOCALNET_SOCKET_URL
            case "mainnet":
                raise NotImplementedError("mainnet not deployed for Sui network yet.")
        self._keypairs, self._addresses, self._address_keypair = load_keys_and_addresses(self.keystore_file)

    @deprecated(version="0.16.1", reason="To support more robust configurations such as sui-base")
    def _d_init__(self, config_path: str, env: str, active_address: str, keystore_file: str, current_url: str) -> None:
        """_d_init__ old init function."""

    def _write_keypair(self, keypair: KeyPair, file_path: str = None) -> None:
        """Register the keypair and write out to keystore file."""
        filepath = file_path if file_path else self.keystore_file
        if os.path.exists(filepath):
            self._keypairs[keypair.serialize()] = keypair
            with open(filepath, "w", encoding="utf8") as keystore:
                keystore.write(json.dumps(self.keystrings, indent=2))
        else:
            raise SuiFileNotFound((filepath))

    def create_new_keypair_and_address(
        self, scheme: SignatureScheme, mnemonics: str = None, derivation_path: str = None
    ) -> tuple[str, KeyPair, SuiAddress]:
        """create_new_keypair_and_address Create a new keypair and address identifier and writes to client.yaml.

        :param scheme: Identifies whether new key is ed25519 or secp256k1
        :type scheme: SignatureScheme
        :param mnemonics: string of phrases separated by spaces, defaults to None
        :type mnemonics: str, optional
        :param derivation_path: The derivation path for key, specific to Signature scheme,
            defaults to root path of scheme
        :type derivation_path: str, optional
        :raises NotImplementedError: When providing unregognized scheme
        :return: The input or generated mnemonic string,a new KeyPair and associated SuiAddress
        :rtype: tuple[str, KeyPair, SuiAddress]
        """
        match scheme:
            case SignatureScheme.ED25519 | SignatureScheme.SECP256K1 | SignatureScheme.SECP256R1:
                mnen, keypair, address = create_new_address(scheme, mnemonics, derivation_path)
                self._addresses[address.address] = address
                self._address_keypair[address.address] = keypair
                self._write_keypair(keypair)
                return mnen, address.identifier
            case _:
                raise NotImplementedError(f"{scheme}: Not recognized as valid keypair scheme.")

    @classmethod
    def _parse_config(cls, fpath: Path, config_file: TextIOWrapper) -> tuple[str, str, str, str, str]:
        """Open configuration file and generalize for ingestion."""
        kfpath = fpath.parent
        sui_config = yaml.safe_load(config_file)
        active_address = sui_config["active_address"] if "active_address" in sui_config else None
        keystore_file = Path(sui_config["keystore"]["File"]) if "keystore" in sui_config else None
        # active_env is new (0.15.0) and identifies the alias in use in the 'envs' map list
        active_env = sui_config["active_env"] if "active_env" in sui_config else None
        if not active_address or not keystore_file or not active_env:
            raise SuiConfigFileError(f"{fpath} is not a valid SUI configuration file.")
        current_url = None
        # Envs is new (0.15.0), it is a list of maps, where the environment
        # contains RPC url identifed by 'aliases' (i.e. devnet, localnet)
        if "envs" in sui_config:
            for envmap in sui_config["envs"]:
                if active_env == envmap["alias"]:
                    current_url = envmap["rpc"]
                    break
        else:
            raise SuiConfigFileError("'envs' not found in configuration file.")
        keystore_file = str(kfpath.joinpath(keystore_file.name).absolute())
        return (str(fpath), active_env, active_address, keystore_file, current_url)

    @classmethod
    @deprecated(version="0.16.0", reason="Accomodate more flexible setup use default_config or sui_base instead.")
    def default(cls) -> "SuiConfig":
        """default Looks for and loads client.yaml from ~/.sui/sui_config.

        :raises SuiFileNotFound: If client.yaml file not found in default path
        :return: An instance of SuiConfig
        :rtype: SuiConfig
        """
        expanded_path = os.path.expanduser(DEFAULT_DEVNET_PATH_STRING)
        if os.path.exists(expanded_path):
            with open(expanded_path, encoding="utf8") as core_file:
                config = super(ClientConfiguration, cls).__new__(cls)
                config._old_init(*cls._parse_config(Path(expanded_path), core_file))
                return config
        else:
            raise SuiFileNotFound(f"{expanded_path} not found.")

    @classmethod
    @deprecated(version="0.16.1", reason="Removing in favor of default or sui_base")
    def from_config_file(cls, infile: str) -> "SuiConfig":
        """from_config_file Load a SuiConfig from a fully qualified path to client.yaml.

        :param infile: Path to client.yaml file to load
        :type infile: str
        :raises SuiFileNotFound: If client.yaml does not exist in path provided
        :return: An instance of SuiConfig
        :rtype: SuiConfig
        """
        expanded_path = os.path.expanduser(infile)
        if os.path.exists(expanded_path):
            with open(expanded_path, encoding="utf8") as core_file:
                config = super(ClientConfiguration, cls).__new__(cls)
                config._old_init(*cls._parse_config(Path(expanded_path), core_file))
                return config
        else:
            raise SuiFileNotFound(f"{expanded_path} not found.")

    @classmethod
    def _new_parse_config(cls, sui_config: str) -> tuple[str, str, str]:
        """New Config Parser."""
        active_address = sui_config["active_address"] if "active_address" in sui_config else None
        keystore_file = Path(sui_config["keystore"]["File"]) if "keystore" in sui_config else None
        # active_env is new (0.15.0) and identifies the alias in use in the 'envs' map list
        active_env = sui_config["active_env"] if "active_env" in sui_config else None
        if not active_address or not keystore_file or not active_env:
            raise SuiConfigFileError("Not a valid SUI configuration file.")
        current_url = None
        if "envs" in sui_config:
            for envmap in sui_config["envs"]:
                if active_env == envmap["alias"]:
                    current_url = envmap["rpc"]
                    break
        else:
            raise SuiConfigFileError("'envs' not found in configuration file.")
        return active_address, current_url, active_env

    @classmethod
    @versionadded(version="0.16.1", reason="More flexible configuration.")
    def _create_config(cls, expanded_path: Path, expanded_binary: Path) -> "SuiConfig":
        """."""
        client_yaml = yaml.safe_load(expanded_path.read_text(encoding="utf8"))
        config = super(ClientConfiguration, cls).__new__(cls)
        config.__init__(str(expanded_path), client_yaml["keystore"]["File"])
        _set_env_vars(expanded_path, expanded_binary)
        config._initiate(*cls._new_parse_config(client_yaml))
        return config

    @classmethod
    @versionadded(version="0.16.1", reason="New loading of default configuration.")
    def default_config(cls) -> "SuiConfig":
        """."""
        expanded_path = Path(os.path.expanduser(DEFAULT_DEVNET_PATH_STRING))
        if expanded_path.exists():
            return cls._create_config(expanded_path, Path(os.path.expanduser(DEFAULT_SUI_BINARY_PATH)))
        raise SuiFileNotFound(f"{expanded_path} not found.")

    @classmethod
    @versionadded(version="0.16.1", reason="Supporting more flexible non-default configurations")
    def sui_base_config(cls) -> "SuiConfig":
        """."""
        return cls._create_config(*sui_base_get_config())

    @classmethod
    @deprecated(version="0.16.1", reason="Never implemented. Will be removed in next version.")
    def _generate_configuration(cls) -> "ClientConfiguration":
        """Generate a default configuration."""
        raise NotImplementedError("SuiConfig.generate_configuration not implemented yet.")

    @property
    def rpc_url(self) -> str:
        """Return the current URL."""
        return self._current_url

    @property
    def local_config(self) -> bool:
        """Return the mode we are running in."""
        return self._local_running

    @property
    def faucet_url(self) -> str:
        """Return faucet url."""
        return self._faucet_url

    @property
    def socket_url(self) -> str:
        """Return socket url."""
        return self._socket_url

    @property
    def active_address(self) -> SuiAddress:
        """Return the current address."""
        return self._active_address

    @property
    def environment(self) -> str:
        """environment Return the current environment of config in use.

        :return: The environment name
        :rtype: str
        """
        return self._current_env

    @property
    def keystore_file(self) -> str:
        """Return the fully qualified keystore path."""
        return self._current_keystore_file

    def set_active_address(self, address: SuiAddress) -> SuiAddress:
        """Change the active address to address."""
        stale_addy = self._active_address
        self._active_address = address
        return stale_addy


# pylint:enable=too-many-instance-attributes
