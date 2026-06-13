import { useEffect } from 'react';
import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useCaseStatus } from '../../api/hooks';

/**
 * Post-upload loading screen: polls the case status every 10s and redirects to
 * the viewer once processing is done. Surfaces per-document failures instead of
 * redirecting.
 */
export default function UploadingPage({ caseId }: { caseId: string }) {
    const navigate = useNavigate();
    const { data: status } = useCaseStatus(caseId);

    const failed = status?.documents.filter((d) => d.processing_status === 'failed') ?? [];
    const hasFailures = failed.length > 0;
    const isDone = status?.status === 'done';

    useEffect(() => {
        if (isDone && !hasFailures) {
            navigate(`/pdf-viewer/${caseId}`);
        }
    }, [isDone, hasFailures, caseId, navigate]);

    if (hasFailures) {
        return (
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 2, px: 4 }}>
                <Alert severity="error" sx={{ borderRadius: 2 }}>
                    Die Verarbeitung ist für mindestens ein Dokument fehlgeschlagen.
                </Alert>
                {failed.map((d) => (
                    <Typography key={d.document_id} color="text.secondary">
                        {d.file_name}: {d.error_message ?? 'Unbekannter Fehler'}
                    </Typography>
                ))}
                <Button variant="contained" onClick={() => navigate('/')} sx={{ textTransform: 'none', borderRadius: 2 }}>
                    Zurück zur Übersicht
                </Button>
            </Box>
        );
    }

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh', gap: 2 }}>
            <CircularProgress />
            <Typography variant="h5">Fall wird verarbeitet…</Typography>
            <Typography color="text.secondary">
                Dies kann einige Minuten dauern. Sie werden automatisch weitergeleitet.
            </Typography>
        </Box>
    );
}
