"""
Voting 25/11/2021.

1. Send X (10,000 DAI * 1.2 in LDO by the spot price) 
   LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb 
   for 10,000 DAI Isidoros Passadis Nov comp (~3433.2799 LDO)
2. Referral program payout of 140246.2696 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb
3. Raisekey limit for Node Operator #12 (Anyblock Analytics) to 1950
"""

import time
from functools import partial
from typing import (
    Dict, Tuple,
    Optional
)
from brownie.network.transaction import TransactionReceipt

from utils.voting import create_vote
from utils.finance import encode_token_transfer
from utils.node_operators import (
    encode_set_node_operator_staking_limit
)
from utils.evm_script import (
    decode_evm_script,
    encode_call_script,
    calls_info_pretty_print
)
from utils.config import (
    prompt_bool,
    get_deployer_account,
    ldo_token_address,
    lido_dao_voting_address,
    lido_dao_token_manager_address,
    lido_dao_finance_address,
    lido_dao_node_operators_registry
)
from utils.agent import agent_forward

try:
    from brownie import interface
except ImportError:
    print(
        'You\'re probably running inside Brownie console. '
        'Please call:\n'
        'set_console_globals(interface=interface)'
    )

def set_console_globals(**kwargs):
    """Extract interface from brownie environment."""
    global interface
    interface = kwargs['interface']

def make_ldo_payout(
        *not_specified,
        target_address: str,
        ldo_in_wei: int,
        reference: str,
        finance: interface.Finance
) -> Tuple[str, str]:
    """Encode LDO payout."""
    if not_specified:
        raise ValueError(
            'Please, specify all arguments with keywords.'
        )

    return encode_token_transfer(
        token_address=ldo_token_address,
        recipient=target_address,
        amount=ldo_in_wei,
        reference=reference,
        finance=finance
    )

def start_vote(
    tx_params: Dict[str, str],
    silent: bool = False
) -> Tuple[int, Optional[TransactionReceipt]]:
    """Prepare and run voting."""

    voting = interface.Voting(lido_dao_voting_address)
    finance = interface.Finance(lido_dao_finance_address)
    token_manager = interface.TokenManager(
        lido_dao_token_manager_address
    )
    registry = interface.NodeOperatorsRegistry(
        lido_dao_node_operators_registry
    )

    anyblock_an_limit = {
        'id': 12,
        'limit': 1950
    }

    _make_ldo_payout = partial(make_ldo_payout, finance=finance)

    _encode_set_node_operator_staking_limit = partial(
        encode_set_node_operator_staking_limit, registry=registry
    )

    encoded_call_script = encode_call_script([
        # 1. Send X (10,000 DAI * 1.2 in LDO by the spot price) 
        #    LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb 
        #    for 10,000 DAI Isidoros Passadis Nov comp

        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=3433.2799 * (10 ** 18),
            reference='Isidoros Passadis Nov comp'
        ),

        # 2. Referral program payout of 140246.2696
        # LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb

        _make_ldo_payout(
            target_address='0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb',
            ldo_in_wei=140246.2696 * (10 ** 18),
            reference="Referral program payout Nov 25"
        ),

        # 3. Raisekey limit for Node Operator #12 (Anyblock Analytics) to 1950

        _encode_set_node_operator_staking_limit(**anyblock_an_limit)

    ])
    human_readable_script = decode_evm_script(
        encoded_call_script, verbose=False, specific_net='mainnet', repeat_is_error=True
    )

    # Show detailed description of prepared voting.
    if not silent:
        print('\nPoints of voting:')
        total = len(human_readable_script)
        print(human_readable_script)
        for ind, call in enumerate(human_readable_script):
            print(f'Point #{ind + 1}/{total}.')
            print(calls_info_pretty_print(call))
            print('---------------------------')

        print('Does it look good?')
        resume = prompt_bool()
        while resume is None:
            resume = prompt_bool()

        if not resume:
            print('Exit without running.')
            return -1, None

    return create_vote(
        voting=voting,
        token_manager=token_manager,
        vote_desc=(
            'Omnibus vote: '
            '1) Send X (10,000 DAI * 1.2 in LDO by the spot price) LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb for 10,000 DAI Isidoros Passadis Nov comp'
            '2) Referral program payout of 140246.2696 LDO to finance multisig 0x48F300bD3C52c7dA6aAbDE4B683dEB27d38B9ABb'
            '3) Raisekey limit for Node Operator #12 (Anyblock Analytics) to 1950'
        ),
        evm_script=encoded_call_script,
        tx_params=tx_params
    )

def main():
    vote_id, _ = start_vote({
        'from': get_deployer_account(),
        'gas_price': '100 gwei'
    })
    print(f'Vote created: {vote_id}.')
    time.sleep(5) # hack for waiting thread #2.