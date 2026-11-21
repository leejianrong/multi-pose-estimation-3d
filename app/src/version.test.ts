import { expect, test } from "vitest";
import { CONTRACT_VERSION } from "./version";

test("contract version is a positive integer", () => {
  expect(Number.isInteger(CONTRACT_VERSION) && CONTRACT_VERSION > 0).toBe(true);
});
