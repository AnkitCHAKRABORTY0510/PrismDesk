import { ThemeToggle } from "../../components/ui/ThemeToggle";

// Navy brand banner used at the top of the login/register cards. The
// wordmark is designed for dark backgrounds, so it always sits on navy.
export function AuthBrand() {
  return (
    <div className="auth-brand">
      <img
        src="/brand/prism-logo.png"
        alt="PRISM Lab — Power-aware Resilient Intelligent Secure Machines"
        width={1200}
        height={405}
        className="auth-logo"
      />
      <div className="auth-rainbow" aria-hidden="true" />
    </div>
  );
}

export function AuthThemeToggle() {
  return (
    <div className="auth-theme">
      <ThemeToggle />
    </div>
  );
}
