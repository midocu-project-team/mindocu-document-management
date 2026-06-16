import React, { useEffect, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { Box, Button, Card, CardContent, IconButton, Tooltip, Typography } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import CloudUploadOutlinedIcon from '@mui/icons-material/CloudUploadOutlined';
import PictureAsPdfIcon from '@mui/icons-material/PictureAsPdf';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutlined';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';

// Bundled (version-matched, offline) worker — same source as the workspace viewer.
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
    'pdfjs-dist/build/pdf.worker.min.mjs',
    import.meta.url,
).toString();

const BRAND = '#1a237e';
const PDF_BASE_WIDTH = 600;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 2.5;

interface PdfEntry {
    name: string;
    url: string;
    file: File;
}

interface PDFViewerReviewProps {
    onValidChange?: (valid: boolean) => void;
    /** Emits the current list of selected PDF files whenever it changes. */
    onFilesChange?: (files: File[]) => void;
    /** Fired when a selection is (partially) rejected because the cap is hit. */
    onLimitReached?: (maxFiles: number) => void;
    maxFiles?: number;
}

function isPdf(file: File): boolean {
    return file.type === 'application/pdf' || file.name.toLowerCase().endsWith('.pdf');
}

export default function PDFViewerReview({
    onValidChange,
    onFilesChange,
    onLimitReached,
    maxFiles = 3,
}: PDFViewerReviewProps) {
    const inputRef = useRef<HTMLInputElement>(null);
    const scrollRef = useRef<HTMLDivElement>(null);
    const pageRefs = useRef<(HTMLDivElement | null)[]>([]);
    const urlsRef = useRef<string[]>([]);
    const dragDepth = useRef(0);

    const [pdfs, setPdfs] = useState<PdfEntry[]>([]);
    const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
    const [pageCounts, setPageCounts] = useState<Record<string, number>>({});
    const [currentPage, setCurrentPage] = useState<number>(1);
    const [inputValue, setInputValue] = useState<string>('1');
    const [zoom, setZoom] = useState<number>(1);
    const [isDragging, setIsDragging] = useState<boolean>(false);

    const selectedPdf = selectedIndex !== null ? pdfs[selectedIndex] : null;
    const numPages = selectedPdf ? (pageCounts[selectedPdf.url] ?? 0) : 0;
    const hasRoom = pdfs.length < maxFiles;

    // Revoke every object URL we created when the component unmounts.
    useEffect(() => {
        urlsRef.current = pdfs.map((p) => p.url);
    }, [pdfs]);
    useEffect(() => () => urlsRef.current.forEach(URL.revokeObjectURL), []);

    // Safety net: a drag that ends outside the component (or is cancelled) never
    // fires our own onDrop/onDragLeave, so reset the drag overlay window-wide.
    useEffect(() => {
        const reset = () => {
            dragDepth.current = 0;
            setIsDragging(false);
        };
        window.addEventListener('dragend', reset);
        window.addEventListener('drop', reset);
        return () => {
            window.removeEventListener('dragend', reset);
            window.removeEventListener('drop', reset);
        };
    }, []);

    function commit(updated: PdfEntry[], nextSelected: number | null) {
        setPdfs(updated);
        setSelectedIndex(nextSelected);
        setCurrentPage(1);
        setInputValue('1');
        onValidChange?.(updated.length > 0);
        onFilesChange?.(updated.map((entry) => entry.file));
    }

    function addFiles(incoming: File[]) {
        const candidates = incoming.filter(isPdf);
        if (candidates.length === 0) return;

        const room = Math.max(0, maxFiles - pdfs.length);
        const accepted = candidates.slice(0, room);
        if (accepted.length < candidates.length) onLimitReached?.(maxFiles);
        if (accepted.length === 0) return;

        const newEntries: PdfEntry[] = accepted.map((f) => ({
            name: f.name,
            url: URL.createObjectURL(f),
            file: f,
        }));
        const updated = [...pdfs, ...newEntries];
        commit(updated, updated.length - 1);
    }

    function removeFile(index: number) {
        const target = pdfs[index];
        const updated = pdfs.filter((_, i) => i !== index);
        if (target) URL.revokeObjectURL(target.url);

        let nextSelected: number | null = selectedIndex;
        if (updated.length === 0) nextSelected = null;
        else if (selectedIndex === null) nextSelected = null;
        else if (index === selectedIndex) nextSelected = Math.min(index, updated.length - 1);
        else if (index < selectedIndex) nextSelected = selectedIndex - 1;
        commit(updated, nextSelected);
    }

    function selectPdf(index: number) {
        setSelectedIndex(index);
        setCurrentPage(1);
        setInputValue('1');
    }

    function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
        addFiles(Array.from(e.target.files ?? []));
        e.target.value = '';
    }

    function handleDragEnter(e: React.DragEvent) {
        e.preventDefault();
        dragDepth.current += 1;
        if (hasRoom) setIsDragging(true);
    }

    function handleDragLeave(e: React.DragEvent) {
        e.preventDefault();
        dragDepth.current -= 1;
        if (dragDepth.current <= 0) {
            dragDepth.current = 0;
            setIsDragging(false);
        }
    }

    function handleDrop(e: React.DragEvent) {
        e.preventDefault();
        dragDepth.current = 0;
        setIsDragging(false);
        addFiles(Array.from(e.dataTransfer.files ?? []));
    }

    function jumpToPage(page: number) {
        const clamped = Math.max(1, Math.min(page, numPages));
        setCurrentPage(clamped);
        setInputValue(String(clamped));
        pageRefs.current[clamped - 1]?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    function handleInputCommit() {
        const parsed = parseInt(inputValue, 10);
        if (!isNaN(parsed)) jumpToPage(parsed);
        else setInputValue(String(currentPage));
    }

    function handleScroll() {
        const container = scrollRef.current;
        if (!container) return;
        const rootRect = container.getBoundingClientRect();
        let bestPage = currentPage;
        let bestVisible = 0;
        pageRefs.current.slice(0, numPages).forEach((ref, i) => {
            if (!ref) return;
            const rect = ref.getBoundingClientRect();
            const visible = Math.min(rect.bottom, rootRect.bottom) - Math.max(rect.top, rootRect.top);
            if (visible > bestVisible) {
                bestVisible = visible;
                bestPage = i + 1;
            }
        });
        if (bestPage !== currentPage) {
            setCurrentPage(bestPage);
            setInputValue(String(bestPage));
        }
    }

    const zoomIn = () => setZoom((z) => Math.min(+(z + 0.2).toFixed(2), MAX_ZOOM));
    const zoomOut = () => setZoom((z) => Math.max(+(z - 0.2).toFixed(2), MIN_ZOOM));

    return (
        <Box
            onDragEnter={handleDragEnter}
            onDragOver={(e) => e.preventDefault()}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            sx={{ position: 'relative', height: '100%', display: 'flex', flexDirection: 'column' }}
        >
            <input
                accept=".pdf,application/pdf"
                type="file"
                multiple
                ref={inputRef}
                onChange={handleFileChange}
                style={{ display: 'none' }}
            />

            {pdfs.length === 0 ? (
                <EmptyDropZone
                    isDragging={isDragging}
                    maxFiles={maxFiles}
                    onBrowse={() => inputRef.current?.click()}
                />
            ) : (
                <Box sx={{ flex: 1, minHeight: 0, display: 'flex', gap: 3 }}>
                    {/* Left: file list */}
                    <Box sx={{ width: 280, flexShrink: 0, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
                        {hasRoom && (
                            <Card
                                variant="outlined"
                                onClick={() => inputRef.current?.click()}
                                sx={{
                                    border: '2px dashed',
                                    borderColor: isDragging ? BRAND : '#c5cae9',
                                    borderRadius: 2,
                                    cursor: 'pointer',
                                    mb: 2,
                                    bgcolor: isDragging ? 'rgba(26,35,126,0.04)' : 'transparent',
                                    transition: 'all 0.15s',
                                    '&:hover': { borderColor: BRAND, bgcolor: 'rgba(26,35,126,0.03)' },
                                }}
                            >
                                <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 2.5, '&:last-child': { pb: 2.5 } }}>
                                    <CloudUploadOutlinedIcon sx={{ color: BRAND, mb: 0.5 }} />
                                    <Typography sx={{ fontWeight: 600, fontSize: 14, color: BRAND }}>
                                        Dateien hinzufügen
                                    </Typography>
                                    <Typography variant="caption" color="text.secondary">
                                        ziehen oder klicken
                                    </Typography>
                                </CardContent>
                            </Card>
                        )}
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
                            {pdfs.length} / {maxFiles} PDFs ausgewählt
                        </Typography>

                        <Box sx={{ flex: 1, minHeight: 0, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 1, pr: 0.5 }}>
                            {pdfs.map((pdf, i) => (
                                <Card
                                    key={pdf.url}
                                    variant="outlined"
                                    sx={{
                                        border: selectedIndex === i ? `2px solid ${BRAND}` : '1px solid #e0e0e0',
                                        borderRadius: 2,
                                        cursor: 'pointer',
                                        transition: 'border-color 0.15s',
                                        '&:hover': { borderColor: BRAND },
                                    }}
                                    onClick={() => selectPdf(i)}
                                >
                                    <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1.5, '&:last-child': { pb: 1.5 } }}>
                                        <PictureAsPdfIcon sx={{ color: '#5c6bc0', fontSize: 34, flexShrink: 0 }} />
                                        <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                                            <Typography sx={{ fontWeight: 600 }} noWrap>
                                                {pdf.name.replace(/\.pdf$/i, '')}
                                            </Typography>
                                            <Typography variant="body2" color="text.secondary">
                                                {pageCounts[pdf.url] ? `${pageCounts[pdf.url]} Seiten` : '…'}
                                            </Typography>
                                        </Box>
                                        <Tooltip title="Entfernen">
                                            <IconButton size="small" onClick={(e) => { e.stopPropagation(); removeFile(i); }}>
                                                <DeleteOutlineIcon fontSize="small" />
                                            </IconButton>
                                        </Tooltip>
                                    </CardContent>
                                </Card>
                            ))}
                        </Box>
                    </Box>

                    {/* Right: PDF viewer */}
                    <Box sx={{ flex: 1, minWidth: 0, minHeight: 0, display: 'flex' }}>
                        {selectedPdf && (
                            <Box sx={{ position: 'relative', flex: 1, minHeight: 0, borderRadius: 3, bgcolor: '#f0f0f0', border: '1px solid #e0e0e0', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
                                <Box
                                    ref={scrollRef}
                                    onScroll={handleScroll}
                                    sx={{ flex: 1, minHeight: 0, overflow: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, py: 3, px: 2 }}
                                >
                                    <Document
                                        file={selectedPdf.url}
                                        onLoadSuccess={({ numPages }) => {
                                            setPageCounts((prev) => ({ ...prev, [selectedPdf.url]: numPages }));
                                            setCurrentPage(1);
                                            setInputValue('1');
                                        }}
                                        loading={<Typography sx={{ color: 'text.secondary', py: 6 }}>PDF wird geladen …</Typography>}
                                        error={<Typography sx={{ color: 'error.main', py: 6 }}>PDF konnte nicht geladen werden.</Typography>}
                                    >
                                        {Array.from({ length: numPages }, (_, i) => (
                                            <Box
                                                key={i}
                                                ref={(el: HTMLDivElement | null) => { pageRefs.current[i] = el; }}
                                                sx={{ borderRadius: 1, overflow: 'hidden', bgcolor: '#fff', boxShadow: '0 4px 16px rgba(0,0,0,0.15)' }}
                                            >
                                                <Page
                                                    pageNumber={i + 1}
                                                    width={Math.round(PDF_BASE_WIDTH * zoom)}
                                                    renderTextLayer={false}
                                                    renderAnnotationLayer={false}
                                                />
                                            </Box>
                                        ))}
                                    </Document>
                                </Box>

                                {/* Floating navigation + zoom toolbar */}
                                <Box sx={{
                                    position: 'absolute',
                                    bottom: 16,
                                    left: '50%',
                                    transform: 'translateX(-50%)',
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 0.5,
                                    bgcolor: 'rgba(255,255,255,0.97)',
                                    borderRadius: 999,
                                    boxShadow: 3,
                                    px: 1,
                                    py: 0.5,
                                }}>
                                    <IconButton size="small" onClick={() => jumpToPage(currentPage - 1)} disabled={currentPage <= 1}>
                                        <KeyboardArrowUpIcon fontSize="small" />
                                    </IconButton>
                                    <Box
                                        component="input"
                                        type="text"
                                        value={inputValue}
                                        onChange={(e: React.ChangeEvent<HTMLInputElement>) => setInputValue(e.target.value)}
                                        onBlur={handleInputCommit}
                                        onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter') handleInputCommit(); }}
                                        sx={{
                                            width: 36,
                                            textAlign: 'center',
                                            border: '1px solid #e0e0e0',
                                            bgcolor: 'white',
                                            borderRadius: 1,
                                            fontSize: 14,
                                            fontWeight: 'bold',
                                            py: 0.5,
                                            outline: 'none',
                                        }}
                                    />
                                    <Typography variant="caption" color="text.secondary" sx={{ minWidth: 28 }}>
                                        / {numPages}
                                    </Typography>
                                    <IconButton size="small" onClick={() => jumpToPage(currentPage + 1)} disabled={currentPage >= numPages}>
                                        <KeyboardArrowDownIcon fontSize="small" />
                                    </IconButton>
                                    <Box sx={{ width: '1px', height: 24, bgcolor: '#e0e0e0', mx: 0.5 }} />
                                    <IconButton size="small" onClick={zoomOut} disabled={zoom <= MIN_ZOOM}>
                                        <ZoomOutIcon fontSize="small" />
                                    </IconButton>
                                    <Typography variant="caption" color="text.secondary" sx={{ minWidth: 40, textAlign: 'center' }}>
                                        {Math.round(zoom * 100)}%
                                    </Typography>
                                    <IconButton size="small" onClick={zoomIn} disabled={zoom >= MAX_ZOOM}>
                                        <ZoomInIcon fontSize="small" />
                                    </IconButton>
                                </Box>
                            </Box>
                        )}
                    </Box>
                </Box>
            )}

            {/* Whole-area drop hint while dragging over a populated view */}
            {isDragging && pdfs.length > 0 && hasRoom && (
                <Box sx={{
                    position: 'absolute',
                    inset: 0,
                    zIndex: 10,
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: 1,
                    bgcolor: 'rgba(26,35,126,0.06)',
                    border: `2px dashed ${BRAND}`,
                    borderRadius: 4,
                    pointerEvents: 'none',
                }}>
                    <CloudUploadOutlinedIcon sx={{ fontSize: 64, color: BRAND }} />
                    <Typography variant="h6" sx={{ color: BRAND, fontWeight: 600 }}>
                        Zum Hinzufügen loslassen
                    </Typography>
                </Box>
            )}
        </Box>
    );
}

interface EmptyDropZoneProps {
    isDragging: boolean;
    maxFiles: number;
    onBrowse: () => void;
}

function EmptyDropZone({ isDragging, maxFiles, onBrowse }: EmptyDropZoneProps) {
    return (
        <Box
            onClick={onBrowse}
            sx={{
                flex: 1,
                minHeight: 0,
                m: 1,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                textAlign: 'center',
                borderRadius: 4,
                border: '2px dashed',
                borderColor: isDragging ? BRAND : '#c5cae9',
                bgcolor: isDragging ? 'rgba(26,35,126,0.04)' : '#fafbff',
                cursor: 'pointer',
                transition: 'all 0.15s',
                '&:hover': { borderColor: BRAND, bgcolor: 'rgba(26,35,126,0.02)' },
            }}
        >
            <CloudUploadOutlinedIcon sx={{ fontSize: 72, color: isDragging ? BRAND : '#9fa8da', mb: 2 }} />
            <Typography variant="h6" sx={{ fontWeight: 600, color: '#37474f' }}>
                PDFs hierher ziehen
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 3 }}>
                oder
            </Typography>
            <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={(e) => { e.stopPropagation(); onBrowse(); }}
                sx={{ borderRadius: 2, px: 4, py: 1.2, textTransform: 'none', fontSize: 16, bgcolor: BRAND }}
            >
                Dateien durchsuchen
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 3 }}>
                Bis zu {maxFiles} PDF-Dateien
            </Typography>
        </Box>
    );
}
