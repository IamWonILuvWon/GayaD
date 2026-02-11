"use client";

import { useEffect, useRef, useState } from "react";

type Props = { url: string; measuresPerPage?: number };

export default function MusicXmlViewer({ url, measuresPerPage = 20 }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const xmlCacheRef = useRef<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setError(null);
      setLoading(true);
      try {
        const res = await fetch(url);
        if (!res.ok) throw new Error(`Failed to fetch musicxml: ${res.status}`);
        const xmlText = await res.text();
        xmlCacheRef.current = xmlText;

        // Try to load OpenSheetMusicDisplay if available
        try {
          const { OpenSheetMusicDisplay } = await import("opensheetmusicdisplay");
          if (cancelled) return;
          if (!containerRef.current) return;

          // helper: build MusicXML string containing only measures [start, end)
          const buildPageXml = (xml: string, startIdx: number, endIdx: number) => {
            const parser = new DOMParser();
            const doc = parser.parseFromString(xml, "application/xml");
            const root = doc.documentElement;
            if (!root) return xml;

            const newDoc = document.implementation.createDocument(null, null);
            const newRoot = newDoc.createElement(root.tagName);
            // copy root attributes
            for (let i = 0; i < root.attributes.length; i++) {
              const at = root.attributes[i];
              newRoot.setAttribute(at.name, at.value);
            }
            newDoc.appendChild(newRoot);

            const partList = doc.getElementsByTagName("part-list")[0];
            if (partList) newRoot.appendChild(newDoc.importNode(partList, true));

            const originalParts = Array.from(doc.getElementsByTagName("part"));
            originalParts.forEach((origPart) => {
              const newPart = newDoc.createElement(origPart.tagName);
              if (origPart.getAttribute("id")) newPart.setAttribute("id", origPart.getAttribute("id")!);

              const measures = Array.from(origPart.getElementsByTagName("measure"));
              const keep = measures.slice(startIdx, endIdx);

              if (keep.length > 0) {
                const first = keep[0];
                const hasAttrs = first.getElementsByTagName("attributes").length > 0;
                if (!hasAttrs) {
                  for (let i = startIdx - 1; i >= 0; i--) {
                    const prev = measures[i];
                    if (!prev) continue;
                    const prevAttrs = prev.getElementsByTagName("attributes")[0];
                    if (prevAttrs) {
                      const imported = newDoc.importNode(prevAttrs, true);
                      first.insertBefore(imported, first.firstChild);
                      break;
                    }
                  }
                }

                keep.forEach((m) => newPart.appendChild(newDoc.importNode(m, true)));
              }

              newRoot.appendChild(newPart);
            });

            // remove title/credit elements
            const removeTags = ["work", "movement-title", "credit", "movement-number"];
            removeTags.forEach((tag) => {
              const nodes = Array.from(newRoot.getElementsByTagName(tag));
              nodes.forEach((n) => n.parentNode?.removeChild(n));
            });

            const serializer = new XMLSerializer();
            let xmlOut = serializer.serializeToString(newDoc);
            const trimmed = xmlOut.trimStart();
            if (!trimmed.startsWith("<?xml")) {
              xmlOut = `<?xml version="1.0" encoding="UTF-8"?>\n${xmlOut}`;
            }
            return xmlOut;
          };

          // count measures
          const countMeasures = (xml: string) => {
            const p = new DOMParser().parseFromString(xml, "application/xml");
            const part = p.getElementsByTagName("part")[0];
            if (!part) return 0;
            return part.getElementsByTagName("measure").length;
          };

          const totalMeasures = countMeasures(xmlText);
          const pages = Math.max(1, Math.ceil(totalMeasures / measuresPerPage));
          setTotalPages(pages);
          if (page > pages) setPage(pages);

          // render current page
          const renderPage = async (pageNum: number) => {
            if (!containerRef.current) return;
            containerRef.current.innerHTML = "";
            const start = (pageNum - 1) * measuresPerPage;
            const end = Math.min(totalMeasures, start + measuresPerPage);
            const pageXml = buildPageXml(xmlText, start, end);

            const osmd = new OpenSheetMusicDisplay(containerRef.current, {
              // drawTitle: true, // title disabled for now
              autoResize: true,
            });

            try {
              await osmd.load(pageXml);
              if (cancelled) return;
              osmd.render();
            } catch (err) {
              console.error("OSMD render error:", err);
              if (containerRef.current) containerRef.current.textContent = pageXml;
            }
          };

          await renderPage(page);
          setLoading(false);
          return;
        } catch (e) {
          // opensheetmusicdisplay not available or failed — fall back to showing XML
          if (cancelled) return;
          containerRef.current!.textContent = xmlText;
          setLoading(false);
          return;
        }
      } catch (err) {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : String(err));
        setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [url, page, measuresPerPage]);

  return (
    <div className="mt-4">
      {loading && <div className="text-sm text-gray-500">로딩 중…</div>}
      {error && <div className="text-sm text-red-600">렌더링 오류: {error}</div>}
      <div ref={containerRef} className="w-full overflow-auto bg-white p-2 border rounded mt-2" />

      <div className="mt-3 flex items-center gap-3">
        <button
          className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300"
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page <= 1 || loading}
        >
          이전
        </button>
        <div className="text-sm text-gray-600">
          페이지 {page} / {totalPages}
        </div>
        <button
          className="px-3 py-1 rounded bg-gray-200 hover:bg-gray-300"
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page >= totalPages || loading}
        >
          다음
        </button>
      </div>
    </div>
  );
}
