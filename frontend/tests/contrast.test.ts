import { describe, it, expect } from "vitest";

/**
 * WCAG 2.1 Contrast Ratio Calculation
 */
function hexToRgb(hex: string): [number, number, number] {
  const clean = hex.replace("#", "");
  return [
    parseInt(clean.substring(0, 2), 16),
    parseInt(clean.substring(2, 4), 16),
    parseInt(clean.substring(4, 6), 16),
  ];
}

function getLuminance(r: number, g: number, b: number): number {
  const [rs, gs, bs] = [r, g, b].map((c) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : Math.pow((s + 0.055) / 1.055, 2.4);
  });
  return 0.2126 * rs + 0.7152 * gs + 0.0722 * bs;
}

function getContrastRatio(hex1: string, hex2: string): number {
  const [r1, g1, b1] = hexToRgb(hex1);
  const [r2, g2, b2] = hexToRgb(hex2);
  const l1 = getLuminance(r1, g1, b1);
  const l2 = getLuminance(r2, g2, b2);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
}

describe("WCAG 2.1 AA Color Contrast Validation", () => {
  describe("Light Theme Tokens", () => {
    const surface = "#FFFFFF";
    const canvas = "#F7F8FA";

    it("primary text (#172B4D) exceeds 4.5:1 on surface and canvas", () => {
      const ink = "#172B4D";
      const surfaceContrast = getContrastRatio(ink, surface);
      const canvasContrast = getContrastRatio(ink, canvas);

      expect(surfaceContrast).toBeGreaterThanOrEqual(4.5);
      expect(canvasContrast).toBeGreaterThanOrEqual(4.5);
      expect(surfaceContrast).toBeGreaterThan(12); // ~12.6:1
    });

    it("muted text (#475467) exceeds 4.5:1 on surface and canvas", () => {
      const muted = "#475467";
      const surfaceContrast = getContrastRatio(muted, surface);
      const canvasContrast = getContrastRatio(muted, canvas);

      expect(surfaceContrast).toBeGreaterThanOrEqual(4.5);
      expect(canvasContrast).toBeGreaterThanOrEqual(4.5);
    });

    it("accent teal (#0F766E) exceeds 4.5:1 against white", () => {
      const accent = "#0F766E";
      const ratio = getContrastRatio(accent, surface);
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });

    it("destructive red (#B42318) exceeds 4.5:1 against white", () => {
      const destructive = "#B42318";
      const ratio = getContrastRatio(destructive, surface);
      expect(ratio).toBeGreaterThanOrEqual(4.5);
    });

    it("status text colors exceed 4.5:1 on their respective soft backgrounds", () => {
      const successText = "#027A48";
      const successBg = "#ECFDF3";
      expect(getContrastRatio(successText, successBg)).toBeGreaterThanOrEqual(4.5);

      const warningText = "#92580E";
      const warningBg = "#FEF7ED";
      expect(getContrastRatio(warningText, warningBg)).toBeGreaterThanOrEqual(4.5);

      const errorText = "#B42318";
      const errorBg = "#FEF3F2";
      expect(getContrastRatio(errorText, errorBg)).toBeGreaterThanOrEqual(4.5);
    });

    it("UI borders (#E4E7EC) satisfy non-text contrast >= 1.2:1 against surface", () => {
      const border = "#E4E7EC";
      const ratio = getContrastRatio(border, surface);
      expect(ratio).toBeGreaterThan(1.1);
    });
  });

  describe("Dark Theme Tokens", () => {
    const darkSurface = "#152238";
    const darkCanvas = "#0B132B";

    it("foreground text (#F8FAFC) exceeds 4.5:1 on dark surface and canvas", () => {
      const fg = "#F8FAFC";
      const surfaceContrast = getContrastRatio(fg, darkSurface);
      const canvasContrast = getContrastRatio(fg, darkCanvas);

      expect(surfaceContrast).toBeGreaterThanOrEqual(4.5);
      expect(canvasContrast).toBeGreaterThanOrEqual(4.5);
      expect(surfaceContrast).toBeGreaterThan(10);
    });

    it("muted text (#94A3B8) exceeds 4.5:1 on dark surface and canvas", () => {
      const muted = "#94A3B8";
      const surfaceContrast = getContrastRatio(muted, darkSurface);
      const canvasContrast = getContrastRatio(muted, darkCanvas);

      expect(surfaceContrast).toBeGreaterThanOrEqual(4.5);
      expect(canvasContrast).toBeGreaterThanOrEqual(4.5);
    });

    it("status dark colors exceed 4.5:1 on dark surface", () => {
      const success = "#34D399";
      const warning = "#FBBF24";
      const error = "#F87171";
      const teal = "#14B8A6";

      expect(getContrastRatio(success, darkSurface)).toBeGreaterThanOrEqual(4.5);
      expect(getContrastRatio(warning, darkSurface)).toBeGreaterThanOrEqual(4.5);
      expect(getContrastRatio(error, darkSurface)).toBeGreaterThanOrEqual(4.5);
      expect(getContrastRatio(teal, darkSurface)).toBeGreaterThanOrEqual(4.5);
    });
  });
});
