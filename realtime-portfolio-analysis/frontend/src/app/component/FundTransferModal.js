import React, { useState, useEffect } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Radio,
  RadioGroup,
  FormControlLabel,
  FormControl,
  TextField,
  Typography,
  Box,
  Alert,
  CircularProgress,
  Divider
} from '@mui/material';
import { styled } from '@mui/material/styles';

const StyledDialog = styled(Dialog)(({ theme }) => ({
  '& .MuiDialog-paper': {
    borderRadius: '12px',
    padding: theme.spacing(2),
    minWidth: '500px'
  }
}));

const BankAccountOption = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  border: '1px solid #e0e0e0',
  borderRadius: '8px',
  marginBottom: theme.spacing(1),
  '&:hover': {
    backgroundColor: '#f5f5f5'
  }
}));

const FundTransferModal = ({ open, onClose, userId, requiredAmount, onTransferSuccess }) => {
  const [bankAccounts, setBankAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [transferAmount, setTransferAmount] = useState(requiredAmount || 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [fetchingAccounts, setFetchingAccounts] = useState(false);

  useEffect(() => {
    if (open && userId) {
      fetchBankAccounts();
    }
    if (requiredAmount) {
      setTransferAmount(requiredAmount);
    }
  }, [open, userId, requiredAmount]);

  const fetchBankAccounts = async () => {
    setFetchingAccounts(true);
    setError('');
    try {
      const response = await fetch(`http://127.0.0.1:8000/api/bank_accounts?user_id=${userId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch bank accounts');
      }
      const data = await response.json();
      setBankAccounts(data.bank_accounts || []);
      if (data.bank_accounts && data.bank_accounts.length > 0) {
        setSelectedAccountId(data.bank_accounts[0].bank_account_id);
      }
    } catch (err) {
      setError('Failed to load bank accounts. Please try again.');
      console.error('Error fetching bank accounts:', err);
    } finally {
      setFetchingAccounts(false);
    }
  };

  const handleTransfer = async () => {
    if (!selectedAccountId) {
      setError('Please select a bank account');
      return;
    }

    if (!transferAmount || transferAmount <= 0) {
      setError('Please enter a valid transfer amount');
      return;
    }

    const selectedAccount = bankAccounts.find(acc => acc.bank_account_id === selectedAccountId);
    if (selectedAccount && transferAmount > selectedAccount.available_balance) {
      setError(`Insufficient funds in selected account. Available: $${selectedAccount.available_balance.toFixed(2)}`);
      return;
    }

    setLoading(true);
    setError('');
    setSuccess('');

    try {
      const response = await fetch(
        `http://127.0.0.1:8000/api/transfer_funds?user_id=${userId}&bank_account_id=${selectedAccountId}&amount=${transferAmount}`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          }
        }
      );

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Transfer failed');
      }

      const data = await response.json();
      setSuccess(`Successfully transferred $${transferAmount.toFixed(2)} to your brokerage account`);

      // Wait a moment to show success message
      setTimeout(() => {
        if (onTransferSuccess) {
          onTransferSuccess(data);
        }
        handleClose();
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to transfer funds. Please try again.');
      console.error('Error transferring funds:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setError('');
    setSuccess('');
    setTransferAmount(requiredAmount || 0);
    onClose();
  };

  const selectedAccount = bankAccounts.find(acc => acc.bank_account_id === selectedAccountId);

  return (
    <StyledDialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        <Typography variant="h5" fontWeight="bold">
          Transfer Funds
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          Transfer funds from your bank account to your brokerage account
        </Typography>
      </DialogTitle>

      <DialogContent>
        {requiredAmount > 0 && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            Insufficient funds. You need ${requiredAmount.toFixed(2)} more to complete this trade.
          </Alert>
        )}

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        {fetchingAccounts ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress />
          </Box>
        ) : (
          <>
            <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 2 }}>
              Select Bank Account
            </Typography>

            <FormControl component="fieldset" fullWidth>
              <RadioGroup
                value={selectedAccountId}
                onChange={(e) => setSelectedAccountId(Number(e.target.value))}
              >
                {bankAccounts.map((account) => (
                  <FormControlLabel
                    key={account.bank_account_id}
                    value={account.bank_account_id}
                    control={<Radio />}
                    label={
                      <BankAccountOption>
                        <Typography variant="body1" fontWeight="bold">
                          {account.bank_name}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {account.account_type} {account.account_number}
                        </Typography>
                        <Typography variant="body2" color="primary" sx={{ mt: 1 }}>
                          Available: ${account.available_balance.toFixed(2)}
                        </Typography>
                      </BankAccountOption>
                    }
                    sx={{ ml: 0, mr: 0, width: '100%' }}
                  />
                ))}
              </RadioGroup>
            </FormControl>

            {bankAccounts.length === 0 && (
              <Alert severity="info">
                No bank accounts found. Please contact support to add a bank account.
              </Alert>
            )}

            <Divider sx={{ my: 3 }} />

            <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 2 }}>
              Transfer Amount
            </Typography>

            <TextField
              fullWidth
              type="number"
              label="Amount"
              value={transferAmount}
              onChange={(e) => setTransferAmount(Number(e.target.value))}
              InputProps={{
                startAdornment: <Typography sx={{ mr: 1 }}>$</Typography>
              }}
              inputProps={{
                min: 0,
                step: 0.01
              }}
              sx={{ mb: 2 }}
            />

            {selectedAccount && (
              <Box sx={{ p: 2, backgroundColor: '#f5f5f5', borderRadius: '8px' }}>
                <Typography variant="body2" color="text.secondary">
                  Remaining balance after transfer:
                </Typography>
                <Typography variant="h6" color={
                  (selectedAccount.available_balance - transferAmount) < 0 ? 'error' : 'success'
                }>
                  ${Math.max(0, selectedAccount.available_balance - transferAmount).toFixed(2)}
                </Typography>
              </Box>
            )}
          </>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} disabled={loading}>
          Cancel
        </Button>
        <Button
          onClick={handleTransfer}
          variant="contained"
          disabled={loading || fetchingAccounts || bankAccounts.length === 0 || success}
          startIcon={loading && <CircularProgress size={20} />}
        >
          {loading ? 'Transferring...' : 'Transfer Funds'}
        </Button>
      </DialogActions>
    </StyledDialog>
  );
};

export default FundTransferModal;
