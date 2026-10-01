import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import UploadDropzone from "@/components/UploadDropzone";
import { LanguageProvider } from "@/lib/i18n";

describe("UploadDropzone Component (Task 14 File Validation)", () => {
  it("1. renders upload component properly with file input", () => {
    const onFileSelected = vi.fn();
    render(
      <LanguageProvider>
        <UploadDropzone onFileSelected={onFileSelected} />
      </LanguageProvider>
    );

    expect(screen.getByText(/أشعة سينية|Chest X-Ray/i)).toBeInTheDocument();
    expect(screen.getByText(/PNG, JPG, JPEG/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /استعراض الملفات المحلية|Browse Local Files/i })).toBeInTheDocument();
  });

  it("2. rejects invalid file types (e.g. document.pdf, script.exe)", () => {
    const onFileSelected = vi.fn();
    const { container } = render(
      <LanguageProvider>
        <UploadDropzone onFileSelected={onFileSelected} />
      </LanguageProvider>
    );

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const invalidFile = new File(["dummy content"], "document.pdf", { type: "application/pdf" });

    fireEvent.change(fileInput, { target: { files: [invalidFile] } });

    expect(screen.getByText(/تنسيق الملف غير مدعوم|Unsupported file format/i)).toBeInTheDocument();
    expect(onFileSelected).not.toHaveBeenCalled();
  });

  it("3. rejects oversized files exceeding 15MB", () => {
    const onFileSelected = vi.fn();
    const { container } = render(
      <LanguageProvider>
        <UploadDropzone onFileSelected={onFileSelected} />
      </LanguageProvider>
    );

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const oversizedFile = new File(["x".repeat(100)], "huge_scan.png", { type: "image/png" });
    Object.defineProperty(oversizedFile, "size", { value: 16 * 1024 * 1024 });

    fireEvent.change(fileInput, { target: { files: [oversizedFile] } });

    expect(screen.getByText(/يتجاوز الملف الحد الأقصى|File exceeds maximum allowed upload size/i)).toBeInTheDocument();
    expect(onFileSelected).not.toHaveBeenCalled();
  });

  it("4. rejects empty (0-byte) files", () => {
    const onFileSelected = vi.fn();
    const { container } = render(
      <LanguageProvider>
        <UploadDropzone onFileSelected={onFileSelected} />
      </LanguageProvider>
    );

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const emptyFile = new File([], "empty.png", { type: "image/png" });
    Object.defineProperty(emptyFile, "size", { value: 0 });

    fireEvent.change(fileInput, { target: { files: [emptyFile] } });

    expect(screen.getByText(/الملف المحدد فارغ|Selected file is empty/i)).toBeInTheDocument();
    expect(onFileSelected).not.toHaveBeenCalled();
  });

  it("5. accepts valid chest X-ray image and calls onFileSelected", () => {
    const onFileSelected = vi.fn();
    const { container } = render(
      <LanguageProvider>
        <UploadDropzone onFileSelected={onFileSelected} />
      </LanguageProvider>
    );

    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const validFile = new File(["valid_image_bytes"], "chest_radiograph.png", { type: "image/png" });
    Object.defineProperty(validFile, "size", { value: 1024 * 500 }); // 500 KB

    fireEvent.change(fileInput, { target: { files: [validFile] } });

    expect(screen.queryByText(/تنسيق الملف غير مدعوم|Unsupported file format/i)).not.toBeInTheDocument();
    expect(onFileSelected).toHaveBeenCalledTimes(1);
    expect(onFileSelected).toHaveBeenCalledWith(validFile);
  });
});
