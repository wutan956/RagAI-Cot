// src/utils/markdown.js
import { nextTick } from 'vue';

export function renderMarkdown(text = '') {
    if (!text) return '';
    text = text.replace(/\\\\\(/g, '\\(')
        .replace(/\\\\\)/g, '\\)')
        .replace(/\\\\\[/g, '\\[')
        .replace(/\\\\]/g, '\\]');
    // ① Markdown → HTML
    const html = marked.parse(text);
    // // ② 渲染数学公式
    // nextTick(() => {
    //     renderMathInElement(document.body, {
    //         delimiters: [
    //             { left: '$$',  right: '$$',  display: true  },
    //             { left: '\\[', right: '\\]', display: true  },
    //             { left: '\\(', right: '\\)', display: false }
    //         ]
    //     });
    // });
    return html;
}