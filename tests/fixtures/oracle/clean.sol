// SPDX-License-Identifier: MIT
// FIXTURE: clean — oracle profile
// Validates updatedAt + answeredInRound for staleness.
pragma solidity ^0.8.0;

interface AggregatorV3Interface {
    function latestRoundData()
        external
        view
        returns (uint80 roundId, int256 answer, uint256 startedAt, uint256 updatedAt, uint80 answeredInRound);
}

contract PriceConsumer {
    AggregatorV3Interface public priceFeed;
    uint256 public constant MAX_STALENESS = 1 hours;

    constructor(AggregatorV3Interface _feed) {
        priceFeed = _feed;
    }

    function getPrice() external view returns (uint256) {
        (uint80 roundId, int256 answer, , uint256 updatedAt, uint80 answeredInRound) =
            priceFeed.latestRoundData();
        require(answer > 0, "bad price");
        require(updatedAt > 0, "incomplete round");
        require(block.timestamp - updatedAt <= MAX_STALENESS, "stale price");
        require(answeredInRound >= roundId, "stale round");
        return uint256(answer);
    }
}
