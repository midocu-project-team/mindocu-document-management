import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  TextField,
} from '@mui/material';
import { useEffect, useState } from 'react';

interface AddCaseDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (name: string) => void;
  title?: string;
  confirmLabel?: string;
  initialValue?: string;
}

export default function AddCaseDialog({
  open,
  onClose,
  onConfirm,
  title = 'Bezeichnung',
  confirmLabel = 'Bestätigen',
  initialValue = '',
}: AddCaseDialogProps) {
  const [name, setName] = useState(initialValue);

  useEffect(() => {
    if (open) setName(initialValue);
  }, [open, initialValue]);

  function handleConfirm() {
    if (!name.trim()) return;
    onConfirm(name.trim());
    setName('');
  }

  function handleClose() {
    setName('');
    onClose();
  }

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="xs" fullWidth>
      <DialogTitle sx={{ fontWeight: 700 }}>{title}</DialogTitle>
      <DialogContent>
        <DialogContentText sx={{ mb: 2 }}>
          Bitte geben Sie dem Fall einen Namen.
        </DialogContentText>
        <TextField
          autoFocus
          fullWidth
          size="small"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleConfirm()}
        />
      </DialogContent>
      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} sx={{ textTransform: 'none' }}>
          Zurück
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={!name.trim()}
          sx={{ textTransform: 'none' }}
        >
          {confirmLabel}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
