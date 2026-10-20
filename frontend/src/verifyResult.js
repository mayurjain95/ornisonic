// Turns /verify responses into what VerifyPanel shows; kept free of React so it's testable on its own.

const FIELD_LABELS = {
  species_name: "species",
  confidence_bps: "confidence",
  ipfs_cid: "IPFS link",
};

export function explorerUrl(onchain) {
  if (!onchain?.contract_address) return null;
  return `https://amoy.polygonscan.com/address/${onchain.contract_address}#readContract`;
}

/** Turns a /verify response into a headline plus one line per check. */
export function describe(body) {
  const { verified, local_valid: localValid, onchain = {} } = body;
  const checks = [];

  if (onchain.checked) {
    if (onchain.error) {
      checks.push({ status: "fail", text: onchain.error });
    } else {
      checks.push(
        onchain.valid
          ? { status: "pass", text: `Audio matches the hash anchored on Polygon (on-chain record #${onchain.onchain_detection_id})` }
          : { status: "fail", text: "Audio does not match the hash anchored on Polygon" }
      );
      checks.push(
        onchain.record_matches_db
          ? { status: "pass", text: "Stored details match the on-chain record" }
          : {
              status: "fail",
              text: `Stored ${onchain.mismatched_fields.map((f) => FIELD_LABELS[f] || f).join(", ")} differ from the on-chain record`,
            }
      );
    }
  } else if (onchain.error) {
    checks.push({ status: "warn", text: "Couldn't reach Polygon, so this was checked against the database only" });
  } else {
    checks.push({ status: "warn", text: "Not anchored on-chain; checked against the database only" });
  }

  checks.push(
    localValid
      ? { status: "pass", text: "Audio matches the database's stored hash" }
      : {
          status: verified ? "warn" : "fail",
          text: verified
            ? "The database's stored hash is wrong; the on-chain record is authoritative"
            : "Audio does not match the database's stored hash",
        }
  );

  let headline;
  if (verified) {
    headline = onchain.checked
      ? "Verified on-chain: this is the original recording."
      : "Verified against the database (not checked on-chain).";
  } else if (onchain.checked && onchain.error) {
    headline = "Not verified: this detection's on-chain record couldn't be found.";
  } else if (onchain.checked && onchain.valid && !onchain.record_matches_db) {
    headline = "The recording is authentic, but this detection's stored details don't match the on-chain record.";
  } else {
    headline = "No match: this file is not the original recording for this detection.";
  }

  return { headline, checks };
}
