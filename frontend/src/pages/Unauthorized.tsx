import { Link } from "react-router";

export default function Unauthorized() {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center">
      <h1 className="text-3xl font-bold">
        403 - Access Denied
      </h1>

      <p className="mt-3">
        You do not have permission to access this page.
      </p>

      <Link
        to="/login"
        className="mt-5 text-blue-600 underline"
      >
        Return to Login
      </Link>
    </div>
  );
}
