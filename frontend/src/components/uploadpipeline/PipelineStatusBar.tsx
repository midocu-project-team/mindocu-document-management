import { Box } from '@mui/material';

interface PipelineStatusBarProps {
    steps: string[];
    currentStep: number; // 1-indexed
}

export default function PipelineStatusBar({ steps, currentStep }: PipelineStatusBarProps) {
    return (
        <Box sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            px: 4,
            py: 1.5,
            bgcolor: 'background.paper',
        }}>

            <Box sx={{ display: 'flex', alignItems: 'center' }}>
                {steps.map((_, i) => {
                    const stepNum = i + 1;
                    const isActive = stepNum === currentStep;
                    const isDone = stepNum < currentStep;
                    return (
                        <Box key={i} sx={{ display: 'flex', alignItems: 'center' }}>
                            <Box sx={{
                                width: 28,
                                height: 28,
                                borderRadius: '50%',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                bgcolor: isActive || isDone ? 'primary.main' : 'action.disabledBackground',
                                color: isActive || isDone ? 'primary.contrastText' : 'text.disabled',
                                fontSize: 13,
                                fontWeight: 'bold',
                                transition: 'background-color 0.2s',
                            }}>
                                {stepNum}
                            </Box>
                            {i < steps.length - 1 && (
                                <Box sx={{
                                    width: 32,
                                    height: 2,
                                    bgcolor: isDone ? 'primary.main' : 'divider',
                                    transition: 'background-color 0.2s',
                                }} />
                            )}
                        </Box>
                    );
                })}
            </Box>
        </Box>
    );
}
