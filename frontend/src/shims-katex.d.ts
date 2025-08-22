// src/shims-katex.d.ts
declare module 'katex/dist/contrib/auto-render.js' {
    export interface RenderOptions {
        delimiters?: Array<{ left: string; right: string; display?: boolean }>;
        ignoredTags?: string[];
    }
    export default function renderMathInElement(
        element: HTMLElement,
        options?: RenderOptions
    ): void;
}