import { Box, Button, Card, CardContent, IconButton, Typography } from '@mui/material';
import GenericHeader from '../GenericHeader';
import { Grid } from '@mui/material';
import { useState } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';
import ArticleIcon from '@mui/icons-material/Article';
import PipelineStatusBar from './PipelineStatusBar';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import AddIcon from '@mui/icons-material/Add';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import ZoomInIcon from '@mui/icons-material/ZoomIn';
import ZoomOutIcon from '@mui/icons-material/ZoomOut';
import PDFViewerReview from './PDFViewerReview';
import UploadingPage from './UploadingPage';
import Checkpoint from './Checkpoint';
import { useNavigate, useParams } from 'react-router-dom';
import { useCases } from '../../context/CasesContext';



const STEPS = ['Hochladen', 'Einverständnis', 'Abschließen'];

export default function PdfUploadReview() {
    const navigator = useNavigate();
    const { caseId } = useParams<{ caseId: string }>();
    const [currentStep, setCurrentStep] = useState<number>(1);
    const [stepValidity, setStepValidity] = useState<Record<number, boolean>>({});
    const { cases, setCaseStatus, addFileToCase } = useCases();
    const currentCase = cases.find(c => c.id === caseId);

    function setValid(step: number, valid: boolean) {
        setStepValidity(prev => ({ ...prev, [step]: valid }));
    }

    const isLastStep = currentStep === STEPS.length;
    const canGoNext = (stepValidity[currentStep] ?? false) || isLastStep;

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
            <PipelineStatusBar caseName={currentCase?.name ?? ''} steps={STEPS} currentStep={currentStep} />
            <GenericHeader title="PDF Upload Review" />

            <Box sx={{ flex: 1, overflow: 'hidden', px: 4, py: 2 }}>
                <Box sx={{ display: currentStep === 1 ? 'flex' : 'none', flexDirection: 'column', height: '100%' }}>
                    <PDFViewerReview
                        onValidChange={v => setValid(1, v)}
                        onFilesAdded={count => caseId && addFileToCase(caseId, count)}
                    />
                </Box>
                <Box sx={{ display: currentStep === 2 ? 'flex' : 'none', flexDirection: 'column', height: '100%' }}>
                    <Checkpoint onValidChange={v => setValid(2, v)} />
                </Box>
                <Box sx={{ display: currentStep === 3 ? 'flex' : 'none', flexDirection: 'column', height: '100%', alignItems: 'center', justifyContent: 'center' }}>
                    <UploadingPage />
                </Box>

            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', px: 4, py: 2, borderTop: '1px solid #e0e0e0' }}>
                <Button
                    variant="outlined"
                    sx={{ borderRadius: 2, px: 4, textTransform: 'none' }}
                    onClick={() => {
                        if (currentStep <= 1) navigator('/');
                        else setCurrentStep(s => s - 1);
                    }}
                >
                    Zurück
                </Button>
                <Button
                    variant="contained"
                    sx={{ borderRadius: 2, px: 4, textTransform: 'none', bgcolor: '#1a237e' }}
                    disabled={!canGoNext}
                    onClick={() => {
                        if (isLastStep){
                            if (caseId) setCaseStatus(caseId, 'processing');
                            navigator('/');
                        }
                        else {
                            setCurrentStep(s => s + 1);
                        }
                    }}
                >
                    {isLastStep ? 'Fertig' : 'Weiter'}
                </Button>
            </Box>
        </Box>
    );
}
