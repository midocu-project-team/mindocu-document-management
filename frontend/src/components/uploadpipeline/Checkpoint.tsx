import { Box, Checkbox, FormControlLabel, Typography } from '@mui/material';
import { useState } from 'react';

const label = 'Ich habe verstanden, dass ich für die fachliche Prüfung und Korrektur der KI-Ausgabe verantworlich bin.';

interface CheckpointProps {
    onValidChange?: (valid: boolean) => void;
}

export default function Checkpoint({ onValidChange }: CheckpointProps) {
    const [checked, setChecked] = useState(false);

    function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
        setChecked(e.target.checked);
        onValidChange?.(e.target.checked);
    }

    return (
        <div>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%' }}>
                <Typography variant="h5" sx={{ mb: 2 }}>
                    Einverständnis
                </Typography>
                <Typography variant="body1" sx={{ mb: 4, textAlign: 'center', maxWidth: 400 }}>
                    Bitte beacten Sie:

Die durch die KI erzeugten Inhalte sind ein automatisch erstellter Entwurf. Sie können Fehler, Auslassungen oder Unstimmigkeiten enthalten. Sie als Gutachter:in sind verpflichtet, die Ergebnisse sorgfältig zu prüfen, zu bewerten und gegebenfalls zu korrigieren. Bitte übernehmen Sie keine Inhalte ungeprüft in Ihre fachliche Ausarbeitung. Mit der Nutzung bestätigen Sie, dass Sie die Verantwortung für die endgültige inhaltliche Richtigkeit tragen.


                </Typography>
                <FormControlLabel
                    control={<Checkbox checked={checked} onChange={handleChange} />}
                    label={label}
                />
            </Box>
        </div>
    );
}
