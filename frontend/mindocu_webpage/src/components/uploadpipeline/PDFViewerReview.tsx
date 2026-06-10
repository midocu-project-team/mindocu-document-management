import React, { useState, useRef, useEffect } from 'react';
import { Document, Page } from 'react-pdf';
import { Box, Button, Card, CardContent, Grid, IconButton, Typography } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import ArticleIcon from '@mui/icons-material/Article';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import { pdfjs } from 'react-pdf';


pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface PdfEntry {
    name: string;
    url: string;
}

interface PDFViewerReviewProps {
    onValidChange?: (valid: boolean) => void;
    onFilesAdded?: (count: number) => void;
}

export default function PDFViewerReview({ onValidChange, onFilesAdded }: PDFViewerReviewProps) {
        const inputRef = useRef<HTMLInputElement>(null);
        const scrollRef = useRef<HTMLDivElement>(null);
        const pageRefs = useRef<(HTMLDivElement | null)[]>([]);
    
        const [pdfs, setPdfs] = useState<PdfEntry[]>([]);
        useEffect(() => { onValidChange?.(pdfs.length > 0); }, [pdfs.length]);
        const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
        const [pageCounts, setPageCounts] = useState<Record<string, number>>({});
        const [currentPage, setCurrentPage] = useState<number>(1);
        const [inputValue, setInputValue] = useState<string>('1');
        const [scale, setScale] = useState<number>(1.0);
    
        const selectedPdf = selectedIndex !== null ? pdfs[selectedIndex] : null;
        const numPages = selectedPdf ? (pageCounts[selectedPdf.url] ?? 0) : 0;
    
        function jumpToPage(page: number) {
            const clamped = Math.max(1, Math.min(page, numPages));
            setCurrentPage(clamped);
            setInputValue(String(clamped));
            pageRefs.current[clamped - 1]?.scrollIntoView({ behavior: 'smooth' });
        }
    
        function handleInputCommit() {
            const parsed = parseInt(inputValue, 10);
            if (!isNaN(parsed)) jumpToPage(parsed);
            else setInputValue(String(currentPage));
        }
        
    function handleScroll() {
        const container = scrollRef.current;
        if (!container) return;
        const containerTop = container.scrollTop;
        const containerBottom = containerTop + container.clientHeight;
        let bestPage = currentPage;
        let bestVisible = 0;
        pageRefs.current.forEach((ref, i) => {
            if (!ref) return;
            const top = ref.offsetTop;
            const bottom = top + ref.offsetHeight;
            const visible = Math.min(bottom, containerBottom) - Math.max(top, containerTop);
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



    function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
        const files = Array.from(e.target.files ?? []);
        if (files.length === 0) return;
        const newEntries: PdfEntry[] = files.map(f => ({ name: f.name, url: URL.createObjectURL(f) }));
        setPdfs(prev => {
            const updated = [...prev, ...newEntries];
            setSelectedIndex(updated.length - 1);
            return updated;
        });
        onFilesAdded?.(newEntries.length);
        setCurrentPage(1);
        setInputValue('1');
        e.target.value = '';
    }
  return (
    <div>
            <Grid container spacing={2} sx={{ p: 2, flexGrow: 1, overflow: 'hidden' }}>
                {/* Left: file list */}
                <Grid size={3}>
                    <input
                        accept=".pdf"
                        type="file"
                        multiple
                        ref={inputRef}
                        onChange={handleFileChange}
                        style={{ display: 'none' }}
                    />
                    <Button
                        variant="contained"
                        startIcon={<AddIcon />}
                        onClick={() => inputRef.current?.click()}
                        fullWidth
                        sx={{ mb: 2, borderRadius: 3, py: 1.5, textTransform: 'none', fontSize: 16 }}
                    >
                        Datei hochladen
                    </Button>

                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                        {pdfs.map((pdf, i) => (
                            <Card
                                key={pdf.url}
                                variant="outlined"
                                sx={{
                                    border: selectedIndex === i ? '2px solid #1a237e' : '1px solid #e0e0e0',
                                    borderRadius: 2,
                                    cursor: 'pointer',
                                    transition: 'border-color 0.15s',
                                }}
                                onClick={() => { setSelectedIndex(i); setCurrentPage(1); setInputValue('1'); }}
                            >
                                <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 1.5, py: 1.5, '&:last-child': { pb: 1.5 } }}>
                                    <ArticleIcon sx={{ color: '#5c6bc0', fontSize: 36, flexShrink: 0 }} />
                                    <Box sx={{ flexGrow: 1, overflow: 'hidden' }}>
                                        <Typography sx={{ fontWeight: 'bold' }} noWrap>
                                            {pdf.name.replace(/\.pdf$/i, '')}
                                        </Typography>
                                        <Typography variant="body2" color="text.secondary">
                                            {pageCounts[pdf.url] ? `${pageCounts[pdf.url]} Seiten` : '…'}
                                        </Typography>
                                    </Box>
                                    <IconButton size="small" onClick={e => e.stopPropagation()}>
                                        <MoreVertIcon />
                                    </IconButton>
                                </CardContent>
                            </Card>
                        ))}
                    </Box>
                </Grid>

                {/* Right: PDF viewer */}
                <Grid size={6}>
                    {selectedPdf && (
                        <Box sx={{ position: 'relative', height: '100%', width: 'fit-content', maxWidth: '100%', mx: 'auto' }}>
                            <Box
                                ref={scrollRef}
                                onScroll={handleScroll}
                                sx={{ overflowY: 'auto', overflowX: 'auto', maxHeight: '75vh' }}
                            >
                                <Document
                                    file={selectedPdf.url}
                                    onLoadSuccess={({ numPages }) => {
                                        setPageCounts(prev => ({ ...prev, [selectedPdf.url]: numPages }));
                                        setCurrentPage(1);
                                        setInputValue('1');
                                    }}
                                >
                                    {Array.from({ length: numPages }, (_, i) => (
                                        <Box
                                            key={i}
                                            ref={(el: HTMLDivElement | null) => { pageRefs.current[i] = el; }}
                                            sx={{ mb: 1 }}
                                        >
                                            <Page pageNumber={i + 1} scale={scale} />
                                        </Box>
                                    ))}
                                </Document>
                            </Box>

                            {/* Floating navigation panel */}
                            <Box sx={{
                                position: 'absolute',
                                bottom: 16,
                                right: 16,
                                bgcolor: 'rgba(240,240,240,0.95)',
                                borderRadius: 2,
                                boxShadow: 3,
                                display: 'flex',
                                flexDirection: 'column',
                                alignItems: 'center',
                                px: 1,
                                py: 0.5,
                                gap: 0.5,
                                minWidth: 48,
                            }}>
                                <Box
                                    component="input"
                                    type="text"
                                    value={inputValue}
                                    onChange={e => setInputValue(e.target.value)}
                                    onBlur={handleInputCommit}
                                    onKeyDown={(e: React.KeyboardEvent) => { if (e.key === 'Enter') handleInputCommit(); }}
                                    sx={{
                                        width: 40,
                                        textAlign: 'center',
                                        border: 'none',
                                        bgcolor: 'white',
                                        borderRadius: 1,
                                        fontSize: 14,
                                        fontWeight: 'bold',
                                        py: 0.5,
                                        outline: 'none',
                                    }}
                                />
                                <Typography variant="caption" color="text.secondary">{numPages}</Typography>
                                <IconButton size="small" onClick={() => jumpToPage(currentPage - 1)} disabled={currentPage <= 1}>
                                    <KeyboardArrowUpIcon fontSize="small" />
                                </IconButton>
                                <IconButton size="small" onClick={() => jumpToPage(currentPage + 1)} disabled={currentPage >= numPages}>
                                    <KeyboardArrowDownIcon fontSize="small" />
                                </IconButton>
                                <IconButton size="small" onClick={() => setScale(s => Math.min(+(s + 0.1).toFixed(1), 3))}>
                                    <ZoomInIcon fontSize="small" />
                                </IconButton>
                                <IconButton size="small" onClick={() => setScale(s => Math.max(+(s - 0.1).toFixed(1), 0.4))}>
                                    <ZoomOutIcon fontSize="small" />
                                </IconButton>
                            </Box>
                        </Box>
                    )}
                </Grid>
            </Grid>
    </div>
  );
}