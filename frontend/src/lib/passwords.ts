import type { PasswordPolicy } from "./api";

export const POLICY_OPTIONS: { value: PasswordPolicy; label: string; hint: string }[] = [
  { value: "easy", label: "Easy", hint: "At least 4 characters. Example: 1234" },
  { value: "standard", label: "Standard", hint: "At least 8 characters, not a common password like 12345678." },
  {
    value: "strong",
    label: "Strong",
    hint: "At least 8 characters with both letters and numbers, not a common password.",
  },
];

export function policyHint(policy: PasswordPolicy | undefined) {
  return POLICY_OPTIONS.find((p) => p.value === policy)?.hint ?? "";
}
