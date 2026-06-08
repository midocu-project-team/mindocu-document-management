import { Box, Typography } from '@mui/material';

interface PipelineStatusBarProps {
    caseName: string;
    steps: string[];
    currentStep: number; // 1-indexed
}

export default function PipelineStatusBar({ caseName, steps, currentStep }: PipelineStatusBarProps) {
    return (
        <Box sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            px: 4,
            py: 1.5,
            bgcolor: '#ffffffff',
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
                                bgcolor: isActive || isDone ? '#1a237e' : '#e0e0e0',
                                color: isActive || isDone ? 'white' : '#9e9e9e',
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
                                    bgcolor: isDone ? '#1a237e' : '#e0e0e0',
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
