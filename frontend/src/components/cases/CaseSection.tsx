import { Box, Button, Typography } from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import type { ReactNode } from 'react';

interface CaseSectionProps {
  title: string;
  emptyMessage: string;
  emptySubtext?: string;
  onAdd?: () => void;
  addLabel?: string;
  children?: ReactNode;
}

export default function CaseSection({
  title,
  emptyMessage,
  emptySubtext,
  onAdd,
  addLabel = 'Hinzufügen',
  children,
}: CaseSectionProps) {
  const hasContent = !!children;

  return (
    <Box sx={{ mb: 4 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="h6" sx={{ fontWeight: 600 }}>
          {title}
        </Typography>
        {onAdd && (
          <Button
            variant="contained"
            size="small"
            startIcon={<AddIcon />}
            onClick={onAdd}
            sx={{ textTransform: 'none', borderRadius: 2 }}
          >
            {addLabel}
          </Button>
        )}
      </Box>

      {hasContent ? (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>{children}</Box>
      ) : (
        <Box
          sx={{
            border: '1.5px dashed',
            borderColor: 'divider',
            borderRadius: 2,
            py: 4,
            px: 2,
            textAlign: 'center',
          }}
        >
          <Typography variant="body2" color="text.secondary" sx={{ fontWeight: 500 }}>
            {emptyMessage}
          </Typography>
          {emptySubtext && (
            <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 0.5 }}>
              {emptySubtext}
            </Typography>
          )}
        </Box>
      )}
    </Box>
  );
}
