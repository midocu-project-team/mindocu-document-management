import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { useCaseStatus } from '../../api/hooks';

/**
 * Post-upload processing screen: the case is processing in the background.
 * "Fertig" returns to the homepage (which polls the case to "Fertige Fälle"),
 * and per-document failures are surfaced if the user stays on the screen.
 */
export default function UploadingPage({ caseId }: { caseId: string }) {
    const navigate = useNavigate();
    const { data: status } = useCaseStatus(caseId);

    const failed = status?.documents.filter((d) => d.processing_status === 'failed') ?? [];
    const hasFailures = failed.length > 0;

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
            <Typography variant="h5">Dokument wird verarbeitet</Typography>
            <Typography color="text.secondary">Das kann einige Minuten dauern.</Typography>
            <Button variant="contained" onClick={() => navigate('/')} sx={{ textTransform: 'none', borderRadius: 2, mt: 1 }}>
                Fertig
            </Button>
        </Box>
    );
}
