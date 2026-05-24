import React from 'react';
import { FileText, Printer } from 'lucide-react';

export default function AuditMemo({ results }) {
  const { memo } = results;

  if (!memo) {
    return (
      <div className="bg-dark-800 border border-dark-700 rounded-2xl p-16 text-center text-gray-500 italic shadow-xl">
        Audit Memo not generated. Please configure LLM_API_KEY in backend variables.
      </div>
    );
  }

  // Simple, elegant Markdown to HTML parser for rendering Claude's output
  const renderMarkdown = (text) => {
    if (!text) return null;

    const lines = text.split('\n');
    return lines.map((line, idx) => {
      const trimmed = line.trim();

      // H1 Header
      if (trimmed.startsWith('# ')) {
        return <h1 key={idx} className="text-3xl font-extrabold text-white mt-8 mb-4 border-b border-dark-750 pb-2">{trimmed.substring(2)}</h1>;
      }
      // H2 Header
      if (trimmed.startsWith('## ')) {
        return <h2 key={idx} className="text-2xl font-bold text-white mt-6 mb-3">{trimmed.substring(3)}</h2>;
      }
      // H3 Header
      if (trimmed.startsWith('### ')) {
        return <h3 key={idx} className="text-xl font-bold text-blue-400 mt-4 mb-2">{trimmed.substring(4)}</h3>;
      }
      // Bullet list items
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        return (
          <li key={idx} className="text-gray-300 ml-6 list-disc mb-1.5 leading-relaxed">
            {parseBoldText(trimmed.substring(2))}
          </li>
        );
      }
      // Number list items
      const numMatch = trimmed.match(/^(\d+)\.\s(.*)/);
      if (numMatch) {
        return (
          <li key={idx} className="text-gray-300 ml-6 list-decimal mb-1.5 leading-relaxed">
            {parseBoldText(numMatch[2])}
          </li>
        );
      }
      // Blockquotes
      if (trimmed.startsWith('> ')) {
        return (
          <blockquote key={idx} className="border-l-4 border-blue-500 bg-dark-950/20 px-4 py-2.5 rounded-r-xl my-4 text-gray-400 italic">
            {parseBoldText(trimmed.substring(2))}
          </blockquote>
        );
      }
      // Empty lines
      if (!trimmed) {
        return <div key={idx} className="h-3" />;
      }
      // Default paragraph
      return <p key={idx} className="text-gray-300 text-sm leading-relaxed mb-3.5">{parseBoldText(trimmed)}</p>;
    });
  };

  // Helper to parse **bold** text in markdown
  const parseBoldText = (text) => {
    const parts = text.split(/\*\*(.*?)\*\*/g);
    return parts.map((part, index) => {
      // odd indices represent matching contents inside double asterisks
      return index % 2 === 1 ? <strong key={index} className="text-white font-bold">{part}</strong> : part;
    });
  };

  const handlePrint = () => {
    window.print();
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto print:bg-white print:text-black">
      {/* Title block */}
      <div className="flex justify-between items-center print:hidden">
        <div>
          <h2 className="text-2xl font-bold text-white mb-1.5 flex items-center gap-2">
            <FileText className="w-6 h-6 text-blue-400" />
            CA Forensic Audit Memo
          </h2>
          <p className="text-sm text-gray-400">Formal Chartered Accountant (CA) observation report compiled dynamically by AI.</p>
        </div>

        <button
          onClick={handlePrint}
          className="bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors flex items-center gap-2"
        >
          <Printer className="w-4 h-4" />
          Download as PDF
        </button>
      </div>

      {/* Styled memo sheet */}
      <div className="bg-dark-800 border border-dark-700 rounded-3xl p-8 md:p-12 shadow-2xl print:border-none print:p-0 print:bg-transparent">
        {/* Memo Header */}
        <div className="border-b border-dark-700 pb-6 mb-8 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <h3 className="text-xl font-bold text-white uppercase tracking-wider">Audit Observation Memo</h3>
            <span className="text-sm text-gray-400">Strictly Private & Confidential</span>
          </div>
          <div className="text-sm text-gray-400 md:text-right">
            <div><strong>Audit Reference:</strong> FA-{results.id?.substring(0, 8).toUpperCase()}</div>
            <div><strong>Classification:</strong> Internal Forensic Assessment</div>
          </div>
        </div>

        {/* Memo Content */}
        <article className="prose prose-invert max-w-none">
          {renderMarkdown(memo.raw_markdown)}
        </article>
      </div>
    </div>
  );
}
