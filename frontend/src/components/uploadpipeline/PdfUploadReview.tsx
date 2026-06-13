import { Alert, Box, Button, Snackbar } from '@mui/material';
import GenericHeader from '../workspace/GenericHeader';
import { useState } from 'react';
import PipelineStatusBar from './PipelineStatusBar';
import PDFViewerReview from './PDFViewerReview';
import UploadingPage from './UploadingPage';
import Checkpoint from './Checkpoint';
import { useNavigate, useParams } from 'react-router-dom';
import { useUploadDocuments } from '../../api/hooks';


const STEPS = ['Hochladen', 'Einverständnis'];
const MAX_FILES = 3;

export default function PdfUploadReview() {
    const navigator = useNavigate();
    const { caseId } = useParams<{ caseId: string }>();
    const [currentStep, setCurrentStep] = useState<number>(1);
    const [stepValidity, setStepValidity] = useState<Record<number, boolean>>({});
    const [files, setFiles] = useState<File[]>([]);
    const [submitted, setSubmitted] = useState(false);
    const [notice, setNotice] = useState<string | null>(null);
    const upload = useUploadDocuments(caseId);

    function setValid(step: number, valid: boolean) {
        setStepValidity(prev => ({ ...prev, [step]: valid }));
    }

    function handleFinish() {
        if (!caseId || files.length === 0) return;
        upload.mutate(files, {
            onSuccess: () => setSubmitted(true),
            onError: (error) =>
                setNotice(error instanceof Error ? error.message : 'Upload fehlgeschlagen.'),
        });
    }

    // The last "Weiter" triggers the upload; on success show the processing screen.
    if (submitted && caseId) {
        return <UploadingPage caseId={caseId} />;
    }

    const isLastStep = currentStep === STEPS.length;
    const canGoNext = stepValidity[currentStep] ?? false;

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', height: '100vh' }}>
            <PipelineStatusBar steps={STEPS} currentStep={currentStep} />
            <GenericHeader title="PDF Upload Review" />

            <Box sx={{ flex: 1, overflow: 'hidden', px: 4, py: 2 }}>
                <Box sx={{ display: currentStep === 1 ? 'flex' : 'none', flexDirection: 'column', height: '100%' }}>
                    <PDFViewerReview
                        maxFiles={MAX_FILES}
                        onValidChange={v => setValid(1, v)}
                        onFilesChange={setFiles}
                        onLimitReached={(max) => setNotice(`Es sind höchstens ${max} PDFs pro Fall erlaubt.`)}
                    />
                </Box>
                <Box sx={{ display: currentStep === 2 ? 'flex' : 'none', flexDirection: 'column', height: '100%' }}>
                    <Checkpoint onValidChange={v => setValid(2, v)} />
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
                    disabled={!canGoNext || upload.isPending}
                    onClick={() => {
                        if (isLastStep) handleFinish();
                        else setCurrentStep(s => s + 1);
                    }}
                >
                    {upload.isPending ? 'Wird hochgeladen…' : 'Weiter'}
                </Button>
            </Box>

            <Snackbar
                open={!!notice}
                autoHideDuration={4000}
                onClose={() => setNotice(null)}
                anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
            >
                <Alert onClose={() => setNotice(null)} severity="warning" variant="filled" sx={{ borderRadius: 2 }}>
                    {notice}
                </Alert>
            </Snackbar>
        </Box>
    );
}
