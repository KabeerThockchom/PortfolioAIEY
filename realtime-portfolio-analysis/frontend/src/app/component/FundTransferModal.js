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
    minWidth: '500px',
    backgroundColor: '#111827', // gray-900
    color: '#f1f5f9', // slate-100
    border: '1px solid #4b5563' // gray-600
  }
}));

const BankAccountOption = styled(Box)(({ theme }) => ({
  padding: theme.spacing(2),
  border: '1px solid #4b5563', // gray-600
  borderRadius: '8px',
  marginBottom: theme.spacing(1),
  backgroundColor: '#1f2937', // gray-800
  '&:hover': {
    backgroundColor: '#374151' // gray-700
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
    console.log('FundTransferModal useEffect - open:', open, 'userId:', userId, 'requiredAmount:', requiredAmount);
    if (open && userId) {
      fetchBankAccounts();
    }
    if (requiredAmount) {
      setTransferAmount(requiredAmount);
    }
  }, [open, userId, requiredAmount]);

  const fetchBankAccounts = async () => {
    console.log('Fetching bank accounts for userId:', userId);
    setFetchingAccounts(true);
    setError('');
    try {
      const url = `http://127.0.0.1:8000/api/bank_accounts?user_id=${userId}`;
      console.log('Fetching from URL:', url);
      const response = await fetch(url);
      console.log('Response status:', response.status);
      if (!response.ok) {
        throw new Error('Failed to fetch bank accounts');
      }
      const data = await response.json();
      console.log('Bank accounts data:', data);
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
        <Typography variant="h5" fontWeight="bold" sx={{ color: '#f1f5f9' }}>
          Transfer Funds
        </Typography>
        <Typography variant="body2" sx={{ mt: 1, color: '#94a3b8' }}>
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
            <CircularProgress sx={{ color: '#3b82f6' }} />
          </Box>
        ) : (
          <>
            <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 2, color: '#f1f5f9' }}>
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
                    control={<Radio sx={{ color: '#94a3b8', '&.Mui-checked': { color: '#3b82f6' } }} />}
                    label={
                      <BankAccountOption>
                        <Typography component="span" variant="body1" fontWeight="bold" sx={{ color: '#f1f5f9', display: 'block' }}>
                          {account.bank_name}
                        </Typography>
                        <Typography component="span" variant="body2" sx={{ color: '#94a3b8', display: 'block' }}>
                          {account.account_type} {account.account_number}
                        </Typography>
                        <Typography component="span" variant="body2" sx={{ mt: 1, color: '#3b82f6', display: 'block' }}>
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

            <Divider sx={{ my: 3, borderColor: '#4b5563' }} />

            <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 2, color: '#f1f5f9' }}>
              Transfer Amount
            </Typography>

            <TextField
              fullWidth
              type="number"
              label="Amount"
              value={transferAmount}
              onChange={(e) => setTransferAmount(Number(e.target.value))}
              InputProps={{
                startAdornment: <Typography sx={{ mr: 1, color: '#f1f5f9' }}>$</Typography>
              }}
              InputLabelProps={{
                sx: { color: '#94a3b8' }
              }}
              inputProps={{
                min: 0,
                step: 0.01
              }}
              sx={{
                mb: 2,
                '& .MuiOutlinedInput-root': {
                  color: '#f1f5f9',
                  backgroundColor: '#1f2937',
                  '& fieldset': {
                    borderColor: '#4b5563'
                  },
                  '&:hover fieldset': {
                    borderColor: '#6b7280'
                  },
                  '&.Mui-focused fieldset': {
                    borderColor: '#3b82f6'
                  }
                }
              }}
            />

            {selectedAccount && (
              <Box sx={{ p: 2, backgroundColor: '#1f2937', border: '1px solid #4b5563', borderRadius: '8px' }}>
                <Typography variant="body2" sx={{ color: '#94a3b8' }}>
                  Remaining balance after transfer:
                </Typography>
                <Typography variant="h6" sx={{
                  color: (selectedAccount.available_balance - transferAmount) < 0 ? '#ef4444' : '#10b981'
                }}>
                  ${Math.max(0, selectedAccount.available_balance - transferAmount).toFixed(2)}
                </Typography>
              </Box>
            )}
          </>
        )}
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button
          onClick={handleClose}
          disabled={loading}
          sx={{
            color: '#94a3b8',
            '&:hover': {
              backgroundColor: '#374151'
            }
          }}
        >
          Cancel
        </Button>
        <Button
          onClick={handleTransfer}
          variant="contained"
          disabled={loading || fetchingAccounts || bankAccounts.length === 0 || success}
          startIcon={loading && <CircularProgress size={20} sx={{ color: '#fff' }} />}
          sx={{
            backgroundColor: '#3b82f6',
            '&:hover': {
              backgroundColor: '#2563eb'
            },
            '&.Mui-disabled': {
              backgroundColor: '#374151',
              color: '#6b7280'
            }
          }}
        >
          {loading ? 'Transferring...' : 'Transfer Funds'}
        </Button>
      </DialogActions>
    </StyledDialog>
  );
};

export default FundTransferModal;
