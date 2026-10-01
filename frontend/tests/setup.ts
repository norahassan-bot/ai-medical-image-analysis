import "@testing-library/jest-dom/vitest";
import { vi } from "vitest";

// Mock URL.createObjectURL and URL.revokeObjectURL
if (typeof window !== "undefined") {
  window.URL.createObjectURL = vi.fn(() => "blob:http://localhost:3000/mock-blob-uuid");
  window.URL.revokeObjectURL = vi.fn();
}
