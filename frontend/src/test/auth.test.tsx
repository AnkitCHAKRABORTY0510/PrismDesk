import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { AxiosError, AxiosHeaders } from "axios";
import { Route, Routes } from "react-router";
import { beforeEach, describe, expect, it, vi } from "vitest";

import ProtectedRoute from "../components/auth/ProtectedRoute";
import Login from "../pages/auth/Login";
import Register from "../pages/auth/Register";
import * as authService from "../services/authService";
import { STUDENT_CAPS, makeUser, renderWithProviders } from "./utils";

vi.mock("../services/authService", () => ({
  getCurrentUser: vi.fn(),
  loginUser: vi.fn(),
  logoutUser: vi.fn(),
  registerUser: vi.fn(),
}));

const mocked = vi.mocked(authService);

function apiError(status: number, detail: unknown) {
  const error = new AxiosError("Request failed");
  error.response = { status, data: { detail }, statusText: "", headers: {}, config: { headers: new AxiosHeaders() } };
  return error;
}

beforeEach(() => {
  vi.resetAllMocks();
  mocked.getCurrentUser.mockRejectedValue(apiError(401, "Authentication required."));
});

describe("Login", () => {
  it("shows the API error for bad credentials", async () => {
    mocked.loginUser.mockRejectedValue(apiError(401, "Invalid username/email or password."));
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<Login />} />
      </Routes>,
      "/login"
    );

    await userEvent.type(await screen.findByLabelText("Username or Email"), "student");
    await userEvent.type(screen.getByLabelText("Password"), "wrong-password");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid username/email or password.");
  });

  it("redirects to the dashboard after login", async () => {
    mocked.loginUser.mockResolvedValue(makeUser(["Student"], STUDENT_CAPS));
    renderWithProviders(
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/dashboard" element={<p>Dashboard page</p>} />
      </Routes>,
      "/login"
    );

    await userEvent.type(await screen.findByLabelText("Username or Email"), "student");
    await userEvent.type(screen.getByLabelText("Password"), "Correct-Horse-42!");
    await userEvent.click(screen.getByRole("button", { name: "Sign In" }));

    expect(await screen.findByText("Dashboard page")).toBeInTheDocument();
    expect(mocked.loginUser).toHaveBeenCalledWith({ identifier: "student", password: "Correct-Horse-42!" });
  });
});

describe("Registration", () => {
  const fill = async (password: string, confirm: string) => {
    await userEvent.type(screen.getByLabelText("Full Name"), "New Student");
    await userEvent.type(screen.getByLabelText("Username"), "new_student");
    await userEvent.type(screen.getByLabelText("Email Address"), "new@prismlab.org");
    await userEvent.type(screen.getByLabelText("Password"), password);
    await userEvent.type(screen.getByLabelText("Confirm Password"), confirm);
    await userEvent.click(screen.getByRole("button", { name: "Create Account" }));
  };

  it("validates matching passwords before calling the API", async () => {
    renderWithProviders(<Register />, "/register");
    await fill("Correct-Horse-42!", "Different-Horse-42!");
    expect(screen.getByRole("alert")).toHaveTextContent("Passwords do not match.");
    expect(mocked.registerUser).not.toHaveBeenCalled();
  });

  it("shows the pending-approval message on success", async () => {
    mocked.registerUser.mockResolvedValue({});
    renderWithProviders(<Register />, "/register");
    await fill("Correct-Horse-42!", "Correct-Horse-42!");
    expect(await screen.findByText("Waiting for Administrator Approval")).toBeInTheDocument();
  });
});

describe("ProtectedRoute", () => {
  const routes = (
    <Routes>
      <Route path="/login" element={<p>Login page</p>} />
      <Route path="/unauthorized" element={<p>Access denied page</p>} />
      <Route element={<ProtectedRoute capability="users.manage" />}>
        <Route path="/admin/users" element={<p>Users page</p>} />
      </Route>
    </Routes>
  );

  it("sends anonymous visitors to login", async () => {
    renderWithProviders(routes, "/admin/users");
    expect(await screen.findByText("Login page")).toBeInTheDocument();
  });

  it("blocks users without the capability", async () => {
    mocked.getCurrentUser.mockResolvedValue(makeUser(["Student"], STUDENT_CAPS));
    renderWithProviders(routes, "/admin/users");
    expect(await screen.findByText("Access denied page")).toBeInTheDocument();
  });

  it("allows users with the capability", async () => {
    mocked.getCurrentUser.mockResolvedValue(makeUser(["Administrator"], ["users.manage"]));
    renderWithProviders(routes, "/admin/users");
    await waitFor(() => expect(screen.getByText("Users page")).toBeInTheDocument());
  });
});
