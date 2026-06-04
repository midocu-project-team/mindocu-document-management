import { Box, Card, CardActionArea, IconButton, ListItemIcon, Menu, MenuItem, Typography } from '@mui/material';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import FolderIcon from '@mui/icons-material/Folder';
import InsertDriveFileOutlinedIcon from '@mui/icons-material/InsertDriveFileOutlined';
import CalendarTodayOutlinedIcon from '@mui/icons-material/CalendarTodayOutlined';
import DriveFileRenameOutlineIcon from '@mui/icons-material/DriveFileRenameOutline';
import DeleteOutlinedIcon from '@mui/icons-material/DeleteOutlined';
import { useState } from 'react';
import type { MouseEvent } from 'react';

interface CaseCardProps {
  name: string;
  fileCount: number;
  createdAt: Date;
  onClick: () => void;
  onRename: () => void;
  onDelete: () => void;
}

export default function CaseCard({ name, fileCount, createdAt, onClick, onRename, onDelete }: CaseCardProps) {
  const [anchor, setAnchor] = useState<HTMLElement | null>(null);

  const formattedDate = createdAt.toLocaleDateString('de-DE', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });

  function openMenu(e: MouseEvent<HTMLButtonElement>) {
    e.stopPropagation();
    setAnchor(e.currentTarget);
  }

  function closeMenu() {
    setAnchor(null);
  }

  function handleRename() {
    closeMenu();
    onRename();
  }

  function handleDelete() {
    closeMenu();
    onDelete();
  }

  return (
    <Card variant="outlined" sx={{ width: 160, position: 'relative', borderRadius: 2 }}>
      <CardActionArea onClick={onClick} sx={{ p: 2, pb: 1 }}>
        <Box sx={{ display: 'flex', justifyContent: 'center', mb: 1 }}>
          <FolderIcon sx={{ fontSize: 48, color: 'text.secondary' }} />
        </Box>
        <Typography variant="body2" sx={{ fontWeight: 600, wordBreak: 'break-word', mb: 1 }}>
          {name}
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <InsertDriveFileOutlinedIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
          <Typography variant="caption" color="text.disabled">
            {fileCount} Dateien
          </Typography>
        </Box>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mt: 0.25 }}>
          <CalendarTodayOutlinedIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
          <Typography variant="caption" color="text.disabled">
            {formattedDate}
          </Typography>
        </Box>
      </CardActionArea>

      <IconButton size="small" sx={{ position: 'absolute', top: 4, right: 4 }} onClick={openMenu}>
        <MoreVertIcon fontSize="small" />
      </IconButton>

      <Menu anchorEl={anchor} open={!!anchor} onClose={closeMenu}>
        <MenuItem onClick={handleRename}>
          <ListItemIcon><DriveFileRenameOutlineIcon fontSize="small" /></ListItemIcon>
          Umbenennen
        </MenuItem>
        <MenuItem onClick={handleDelete} sx={{ color: 'error.main' }}>
          <ListItemIcon><DeleteOutlinedIcon fontSize="small" color="error" /></ListItemIcon>
          Datei löschen
        </MenuItem>
      </Menu>
    </Card>
  );
}
