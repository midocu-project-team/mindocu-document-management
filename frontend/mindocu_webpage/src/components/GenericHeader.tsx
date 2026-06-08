
import { Box } from '@mui/material';
import Typography from '@mui/material/Typography';



export default function GenericHeader({ title }: { title: string }) {
  return (
    <Box sx={{ mb: 4, borderBottom: '1px solid', borderColor: 'divider', pb: 2 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        {title}
      </Typography>
    </Box>
  );
}