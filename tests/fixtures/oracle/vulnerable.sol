// SPDX-License-Identifier: MIT
// FIXTURE: vulnerable — oracle profile
// Bug: getPrice() reads latestRoundData but does not validate updatedAt
// staleness. A stale price (e.g. from a paused feed) is accepted.
// Expected vulnerability_type: oracle_staleness
pragma solidity ^0.8.0;

interface AggregatorV3Interface {
    function latestRoundData()
        external
        view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
}

contract PriceConsumer {
    AggregatorV3Interface public priceFeed;

    constructor(AggregatorV3Interface _feed) {
        priceFeed = _feed;
    }

    function getPrice() external view returns (uint256) {
        (, int256 answer, , , ) = priceFeed.latestRoundData();
        require(answer > 0, "bad price");
        return uint256(answer);
    }
}
