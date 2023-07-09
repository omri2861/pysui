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


"""pysui Asynchronous client example.

Shows:
* Loading an asynchronous client (see `main`)
* Fetching all address owned object descriptors from Sui blockchain
* Fetching all address owned gas objects for each address from Sui blockchain
* Note that there are new SUI RPC API that can simplify this further and pysui has
* builders for them. See pysui/sui/sui_builders/get_builders.py:
*   GetCoinMetaData
*   GetCoinTypeBalance
*   GetCoins
"""

import asyncio
import os
import pathlib
import sys
import json


PROJECT_DIR = pathlib.Path(os.path.dirname(__file__))
PARENT = PROJECT_DIR.parent

sys.path.insert(0, str(PROJECT_DIR))
sys.path.insert(0, str(PARENT))
sys.path.insert(0, str(os.path.join(PARENT, "pysui")))

from pysui import AsyncClient, SuiConfig, SuiAddress
from pysui.sui.sui_constants import SUI_COIN_DENOMINATOR
from pysui.sui.sui_txresults.single_tx import (
    ObjectReadPage,
    SuiCoinObjects,
    SuiGas,
)


def object_stats(objs: list[ObjectReadPage]) -> None:
    """object_stats Print stats about objects for address.

    :param objs: List of object descriptors
    :type objs: list[ObjectInfo]
    """
    obj_types = {}
    for desc in objs.data:
        if desc.object_type not in obj_types:
            obj_types[desc.object_type] = 0
        obj_types[desc.object_type] = obj_types[desc.object_type] + 1
    print(f"owned types and counts:\n{json.dumps(obj_types,indent=2)}")


def print_gas(gasses: SuiCoinObjects) -> int:
    """print_gas Prints gas balances for each gas object `gasses`.

    :param gasses: A list of SuiGas type objects
    :type gasses: list[SuiGas]
    :return: Total gas summed from all SuiGas in gasses
    :rtype: int
    """
    total: int = 0
    for gas_result in gasses.data:
        total += int(gas_result.balance)
        print(
            f"{gas_result.coin_object_id} has {int(gas_result.balance):12} -> {int(gas_result.balance)/SUI_COIN_DENOMINATOR:.8f}"
        )
    print(f"Total gas {total:12} -> {total/SUI_COIN_DENOMINATOR:.8f}")
    print()
    return total


async def get_all_gas(client: AsyncClient) -> dict[SuiAddress, list[SuiGas]]:
    """get_all_gas Gets all SuiGas for each address in configuration.

    :param client: Asynchronous Sui Client
    :type client: SuiAsynchClient
    :return: Dictionary of all gas objects for each address
    :rtype: dict[SuiAddress, list[SuiGas]]
    """
    config: SuiConfig = client.config
    addys = [SuiAddress(x) for x in config.addresses]
    addy_list = [client.get_gas(x, True) for x in addys]
    gresult = await asyncio.gather(*addy_list, return_exceptions=True)
    return_map = {}
    for index, gres in enumerate(gresult):
        return_map[addys[index]] = gres.result_data
    return return_map


async def main_run(client: AsyncClient):
    """main Asynchronous entry point."""
    config: SuiConfig = client.config
    owned_objects = asyncio.create_task(client.get_objects())
    gasses = asyncio.create_task(get_all_gas(client))
    print(f"Getting owned objects for: {config.active_address}")
    result = await owned_objects
    object_stats(result.result_data)
    result = await gasses
    grand_total: int = 0
    for key, value in result.items():
        print(f"\nGas objects for: {key.identifier}")
        grand_total += print_gas(value)
        print()
    print(
        f"Grand Total gas {grand_total:12} -> {grand_total/SUI_COIN_DENOMINATOR:.8f}\n"
    )
    print("Exiting async pysui")


def main():
    """Setup asynch loop and run."""
    arg_line = sys.argv[1:].copy()
    # Handle a different client.yaml than default
    if arg_line and arg_line[0] == "--local":
        cfg = SuiConfig.sui_base_config()
    else:
        cfg = SuiConfig.default_config()
    arpc = AsyncClient(cfg)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main_run(arpc))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
