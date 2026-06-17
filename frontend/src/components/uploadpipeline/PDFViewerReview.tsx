import React, { useEffect, useRef, useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import { useVirtualizer } from '@tanstack/react-virtual';
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

const PDF_BASE_WIDTH = 600;
const PDF_PAGE_GAP = 16;            // vertical gap between rendered pages (px)
const PDF_DEFAULT_ASPECT = 1.414;   // A4 portrait fallback until a page is measured
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
    const pageWidth = Math.round(PDF_BASE_WIDTH * zoom);

    // Only the pages in (and just outside) the viewport are mounted as canvases;
    // everything else is a sized placeholder slot. measureElement swaps the
    // A4 estimate for each page's real height once it has rendered.
    const rowVirtualizer = useVirtualizer({
        count: numPages,
        getScrollElement: () => scrollRef.current,
        estimateSize: () => Math.round(pageWidth * PDF_DEFAULT_ASPECT) + PDF_PAGE_GAP,
        overscan: 2,
    });

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

    // A zoom change resizes every page, so the cached heights are stale — drop
    // them back to the (zoom-scaled) estimate and let measureElement re-measure.
    useEffect(() => {
        rowVirtualizer.measure();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [zoom]);

    // Reset the scroll position to the top when switching to another PDF.
    useEffect(() => {
        scrollRef.current?.scrollTo({ top: 0 });
    }, [selectedPdf?.url]);

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
        rowVirtualizer.scrollToIndex(clamped - 1, { align: 'start', behavior: 'smooth' });
    }

    function handleInputCommit() {
        const parsed = parseInt(inputValue, 10);
        if (!isNaN(parsed)) jumpToPage(parsed);
        else setInputValue(String(currentPage));
    }

    function handleScroll() {
        const container = scrollRef.current;
        if (!container || numPages === 0) return;
        // The page whose slot straddles the viewport's vertical centre is "current".
        const center = container.scrollTop + container.clientHeight / 2;
        const items = rowVirtualizer.getVirtualItems();
        let bestPage = currentPage;
        for (const item of items) {
            if (center >= item.start && center < item.start + item.size) {
                bestPage = item.index + 1;
                break;
            }
        }
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
                                    borderColor: isDragging ? 'primary.main' : 'divider',
                                    borderRadius: 2,
                                    cursor: 'pointer',
                                    mb: 2,
                                    bgcolor: isDragging ? 'action.hover' : 'transparent',
                                    transition: 'all 0.15s',
                                    '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
                                }}
                            >
                                <CardContent sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', py: 2.5, '&:last-child': { pb: 2.5 } }}>
                                    <CloudUploadOutlinedIcon sx={{ color: 'primary.main', mb: 0.5 }} />
                                    <Typography sx={{ fontWeight: 600, fontSize: 14, color: 'primary.main' }}>
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
                                        border: selectedIndex === i ? '2px solid' : '1px solid',
                                        borderColor: selectedIndex === i ? 'primary.main' : 'divider',
                                        borderRadius: 2,
                                        cursor: 'pointer',
                                        transition: 'border-color 0.15s',
                                        '&:hover': { borderColor: 'primary.main' },
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
                            <Box sx={(theme) => ({ position: 'relative', flex: 1, minHeight: 0, borderRadius: 3, bgcolor: theme.palette.mode === 'dark' ? '#0f1014' : '#f0f0f0', border: '1px solid', borderColor: 'divider', overflow: 'hidden', display: 'flex', flexDirection: 'column' })}>
                                <Box
                                    ref={scrollRef}
                                    onScroll={handleScroll}
                                    sx={{ flex: 1, minHeight: 0, overflow: 'auto', py: 3, px: 2 }}
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
                                        <Box sx={{ position: 'relative', width: '100%', height: rowVirtualizer.getTotalSize() }}>
                                            {rowVirtualizer.getVirtualItems().map((item) => (
                                                <Box
                                                    key={item.key}
                                                    data-index={item.index}
                                                    ref={rowVirtualizer.measureElement}
                                                    sx={{
                                                        position: 'absolute',
                                                        top: 0,
                                                        left: 0,
                                                        width: '100%',
                                                        transform: `translateY(${item.start}px)`,
                                                        display: 'flex',
                                                        justifyContent: 'center',
                                                        pb: `${PDF_PAGE_GAP}px`,
                                                    }}
                                                >
                                                    <Box sx={{ borderRadius: 1, overflow: 'hidden', bgcolor: '#fff', boxShadow: '0 4px 16px rgba(0,0,0,0.15)', width: pageWidth }}>
                                                        <Page
                                                            pageNumber={item.index + 1}
                                                            width={pageWidth}
                                                            renderTextLayer={false}
                                                            renderAnnotationLayer={false}
                                                            loading={<Box sx={{ width: pageWidth, height: Math.round(pageWidth * PDF_DEFAULT_ASPECT) }} />}
                                                        />
                                                    </Box>
                                                </Box>
                                            ))}
                                        </Box>
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
                                    bgcolor: 'background.paper',
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
                                            border: '1px solid',
                                            borderColor: 'divider',
                                            bgcolor: 'background.paper',
                                            color: 'text.primary',
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
                                    <Box sx={{ width: '1px', height: 24, bgcolor: 'divider', mx: 0.5 }} />
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
                    bgcolor: 'action.hover',
                    border: '2px dashed',
                    borderColor: 'primary.main',
                    borderRadius: 4,
                    pointerEvents: 'none',
                }}>
                    <CloudUploadOutlinedIcon sx={{ fontSize: 64, color: 'primary.main' }} />
                    <Typography variant="h6" sx={{ color: 'primary.main', fontWeight: 600 }}>
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
                borderColor: isDragging ? 'primary.main' : 'divider',
                bgcolor: isDragging ? 'action.hover' : 'background.paper',
                cursor: 'pointer',
                transition: 'all 0.15s',
                '&:hover': { borderColor: 'primary.main', bgcolor: 'action.hover' },
            }}
        >
            <CloudUploadOutlinedIcon sx={{ fontSize: 72, color: isDragging ? 'primary.main' : 'text.secondary', mb: 2 }} />
            <Typography variant="h6" sx={{ fontWeight: 600, color: 'text.primary' }}>
                PDFs hierher ziehen
            </Typography>
            <Typography color="text.secondary" sx={{ mb: 3 }}>
                oder
            </Typography>
            <Button
                variant="contained"
                startIcon={<AddIcon />}
                onClick={(e) => { e.stopPropagation(); onBrowse(); }}
                sx={{ borderRadius: 2, px: 4, py: 1.2, textTransform: 'none', fontSize: 16, bgcolor: 'primary.main' }}
            >
                Dateien durchsuchen
            </Button>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 3 }}>
                Bis zu {maxFiles} PDF-Dateien
            </Typography>
        </Box>
    );
}
