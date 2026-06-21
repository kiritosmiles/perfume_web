declare module "html-to-image" {
  export function toPng(
    node: HTMLElement,
    options?: {
      backgroundColor?: string;
      pixelRatio?: number;
      cacheBust?: boolean;
      width?: number;
      height?: number;
      style?: Record<string, string>;
      quality?: number;
    }
  ): Promise<string>;
}
