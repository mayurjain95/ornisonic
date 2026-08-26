// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title DetectionRegistry
/// @notice Anchors tamper-proof records of endangered-species audio detections.
/// Anyone can submit a record; anyone can verify one by re-hashing the original
/// audio + result and comparing against what's stored on-chain.
contract DetectionRegistry {
    struct Detection {
        bytes32 audioHash;      // keccak256 hash of the raw audio bytes
        string ipfsCid;         // IPFS content address of the stored audio
        string speciesName;     // scientific name
        uint16 confidenceBps;   // confidence score, basis points (0-10000 = 0-100%)
        uint256 timestamp;      // block timestamp at anchor time
        address submitter;      // who anchored this record
    }

    Detection[] public detections;

    event DetectionAnchored(
        uint256 indexed id,
        bytes32 indexed audioHash,
        string speciesName,
        uint256 timestamp,
        address submitter
    );

    function anchorDetection(
        bytes32 audioHash,
        string calldata ipfsCid,
        string calldata speciesName,
        uint16 confidenceBps
    ) external returns (uint256 id) {
        require(confidenceBps <= 10000, "confidence out of range");

        detections.push(Detection({
            audioHash: audioHash,
            ipfsCid: ipfsCid,
            speciesName: speciesName,
            confidenceBps: confidenceBps,
            timestamp: block.timestamp,
            submitter: msg.sender
        }));

        id = detections.length - 1;
        emit DetectionAnchored(id, audioHash, speciesName, block.timestamp, msg.sender);
    }

    function verify(uint256 id, bytes32 audioHash) external view returns (bool) {
        require(id < detections.length, "no such detection");
        return detections[id].audioHash == audioHash;
    }

    function totalDetections() external view returns (uint256) {
        return detections.length;
    }

    function getDetection(uint256 id) external view returns (Detection memory) {
        require(id < detections.length, "no such detection");
        return detections[id];
    }
}
