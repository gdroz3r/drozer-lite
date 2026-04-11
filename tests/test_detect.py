"""Tests for the deterministic profile detection engine."""

from __future__ import annotations

from drozer_lite.detect import detect_profiles, select_profiles


def _file(content: str, name: str = "Test.sol") -> list[tuple[str, str]]:
    return [(name, content)]


def test_universal_always_selected_on_empty_source() -> None:
    sel = detect_profiles(_file(""))
    assert "universal" in sel.selected
    assert sel.source == "auto"


def test_vault_detected_from_erc4626_keywords() -> None:
    src = """
    contract MyVault is ERC4626 {
        function deposit(uint a) public {}
        function withdraw(uint a) public {}
        function totalAssets() public view returns (uint) {}
        function previewDeposit(uint a) public view returns (uint) {}
    }
    """
    sel = detect_profiles(_file(src))
    assert "universal" in sel.selected
    assert "vault" in sel.selected
    assert sel.scores["vault"] >= 3


def test_signature_detected_from_eip712() -> None:
    src = """
    bytes32 DOMAIN_SEPARATOR;
    function permit(address owner, address spender) public {
        bytes32 digest = _hashTypedDataV4(structHash);
        address signer = ecrecover(digest, v, r, s);
    }
    """
    sel = detect_profiles(_file(src))
    assert "signature" in sel.selected


def test_below_threshold_not_selected() -> None:
    # Only one weak match, should not select vault.
    src = "function deposit(uint a) public {}"
    sel = detect_profiles(_file(src))
    assert "vault" not in sel.selected
    assert "universal" in sel.selected


def test_explicit_only_profiles_never_auto_selected() -> None:
    # Even with Solana/ICP keywords in the source, they should never auto-select.
    src = "// solana anchor canister ic-cdk"
    sel = detect_profiles(_file(src))
    assert "icp" not in sel.selected
    assert "solana" not in sel.selected


def test_select_profiles_user_override_loads_explicit_only() -> None:
    sel = select_profiles(_file(""), override="icp")
    assert "icp" in sel.selected
    assert "universal" in sel.selected
    assert sel.source == "user-override"


def test_select_profiles_auto_passthrough() -> None:
    sel = select_profiles(_file(""), override="auto")
    assert sel.source == "auto"


def test_select_profiles_none_passthrough() -> None:
    sel = select_profiles(_file(""), override=None)
    assert sel.source == "auto"


def test_dex_detected_from_swap_keywords() -> None:
    src = """
    import "IUniswapV3Pool.sol";
    contract Router is ISwapRouter {
        uint160 sqrtPriceX96;
        function swap(uint256 amountIn, uint256 amountOutMin) external {}
        function addLiquidity() external {}
    }
    """
    sel = detect_profiles(_file(src))
    assert "dex" in sel.selected


def test_multiple_profiles_can_select_simultaneously() -> None:
    src = """
    contract LendingVault is ERC4626 {
        function deposit(uint a) public {}
        function withdraw(uint a) public {}
        function totalAssets() public view returns (uint) {}
        function borrow(uint a) external {}
        function liquidate(address user) external {}
        uint256 public collateral;
        uint256 public healthFactor;
        uint256 public LTV;
    }
    """
    sel = detect_profiles(_file(src))
    assert "vault" in sel.selected
    assert "lending" in sel.selected
