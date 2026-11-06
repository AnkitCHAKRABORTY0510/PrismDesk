import { describe, expect, it } from "vitest";

import { countdown, splitList } from "../lib/format";
import { can, navigationFor } from "../lib/permissions";
import { ADMIN_CAPS, GUEST_CAPS, STUDENT_CAPS, makeUser } from "./utils";

describe("format helpers", () => {
  it("shows time left and overdue countdowns", () => {
    const now = new Date("2026-11-06T12:00:00Z");
    expect(countdown("2026-11-08T15:30:00Z", now)).toBe("2d 3h left");
    expect(countdown("2026-11-06T12:45:00Z", now)).toBe("45m left");
    expect(countdown("2026-11-05T10:00:00Z", now)).toBe("1d 2h overdue");
  });

  it("splits comma and newline separated lists", () => {
    expect(splitList("a, b\n c,,")).toEqual(["a", "b", "c"]);
  });
});

describe("role-based navigation", () => {
  const labels = (caps: string[], roles: string[]) =>
    navigationFor(makeUser(roles, caps)).map((item) => item.label);

  it("gives students workspace items but no administration", () => {
    const items = labels(STUDENT_CAPS, ["Student"]);
    expect(items).toEqual(expect.arrayContaining(["Projects", "Research Library", "Tasks", "Handbook", "Conferences"]));
    expect(items).not.toContain("User Management");
    expect(items).not.toContain("Audit Logs");
  });

  it("gives administrators the administration section", () => {
    expect(labels(ADMIN_CAPS, ["Administrator"])).toEqual(
      expect.arrayContaining(["User Management", "Audit Logs", "Announcements", "System Settings"])
    );
  });

  it("restricts guests to read-only areas", () => {
    const items = labels(GUEST_CAPS, ["Guest"]);
    expect(items).toEqual(["Dashboard", "Projects", "Conferences", "Notifications"]);
  });

  it("checks capabilities, not role names", () => {
    expect(can(makeUser(["Professor"], ["tasks.review"]), "tasks.review")).toBe(true);
    expect(can(null, "tasks.review")).toBe(false);
  });
});
