import React, { useState, useEffect } from 'react';
import {
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
  Divider,
  Card,
  CardContent
} from '@mui/material';
import { styled } from '@mui/material/styles';

const StyledCard = styled(Card)(({ theme }) => ({
  borderRadius: '16px',
  backgroundColor: '#111827', // gray-900
  color: '#f1f5f9', // slate-100
  border: '1px solid #4b5563', // gray-600
  boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
  width: '100%',
  maxWidth: '28rem' // max-w-md
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

const FundTransferPanel = ({ userId, requiredAmount, transferCompleteTrigger, lastTransferAmount, onTransferSuccess, onClear }) => {
  const [bankAccounts, setBankAccounts] = useState([]);
  const [selectedAccountId, setSelectedAccountId] = useState('');
  const [transferAmount, setTransferAmount] = useState(requiredAmount || 0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [fetchingAccounts, setFetchingAccounts] = useState(false);
  const [transferStatus, setTransferStatus] = useState('idle'); // 'idle', 'success', 'cancelled'
  const [finalAmount, setFinalAmount] = useState(0);

  useEffect(() => {
    console.log('FundTransferPanel useEffect - userId:', userId, 'requiredAmount:', requiredAmount);
    if (userId) {
      fetchBankAccounts();
    }
    if (requiredAmount) {
      setTransferAmount(requiredAmount);
    }
  }, [userId, requiredAmount]);

  // Watch for voice transfer completion OR cancellation
  useEffect(() => {
    if (transferCompleteTrigger > 0 && userId) {
      console.log('Voice transfer trigger received');
      console.log('Voice transfer amount:', lastTransferAmount);

      // Check if it's a cancellation (amount = 0) or successful transfer
      if (lastTransferAmount === 0) {
        console.log('Voice transfer cancelled by user');
        setTransferStatus('cancelled');
        setFinalAmount(0);
      } else {
        console.log('Voice transfer completed successfully');
        setTransferStatus('success');
        setFinalAmount(lastTransferAmount || transferAmount || requiredAmount || 0);
      }
      fetchBankAccounts();
    }
  }, [transferCompleteTrigger]);

  // Auto-dismiss after 10 seconds for success or cancelled status
  useEffect(() => {
    if (transferStatus === 'success' || transferStatus === 'cancelled') {
      console.log(`Transfer ${transferStatus}, will auto-dismiss in 10 seconds`);
      const timer = setTimeout(() => {
        console.log('Auto-dismissing transfer panel');
        if (onClear) {
          onClear(); // Close the panel
        }
      }, 10000); // 10 seconds

      // Cleanup: clear timer if component unmounts or status changes
      return () => {
        clearTimeout(timer);
      };
    }
  }, [transferStatus, onClear]);

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
      // Insufficient funds - mark as cancelled
      setTransferStatus('cancelled');
      setFinalAmount(transferAmount);
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

      // Mark as successful and save final amount
      setTransferStatus('success');
      setFinalAmount(transferAmount);

      // Call success callback
      if (onTransferSuccess) {
        onTransferSuccess(data);
      }

      // Refresh bank accounts to show updated balances
      await fetchBankAccounts();
    } catch (err) {
      setError(err.message || 'Failed to transfer funds. Please try again.');
      console.error('Error transferring funds:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    setError('');
    setSuccess('');
    setTransferAmount(requiredAmount || 0);
    setSelectedAccountId(bankAccounts.length > 0 ? bankAccounts[0].bank_account_id : '');
    setTransferStatus('idle');
    setFinalAmount(0);
    if (onClear) {
      onClear();
    }
  };

  const selectedAccount = bankAccounts.find(acc => acc.bank_account_id === selectedAccountId);

  return (
    <StyledCard>
      <CardContent sx={{ p: 3 }}>
        {/* Header */}
        <Box sx={{ mb: 3 }}>
          <Typography variant="h6" fontWeight="bold" sx={{ color: '#f1f5f9', mb: 0.5 }}>
            Transfer Funds
          </Typography>
          <Typography variant="body2" sx={{ color: '#94a3b8' }}>
            Transfer funds from your bank account to your brokerage account
          </Typography>
        </Box>

        {/* Transfer Status Message */}
        {transferStatus === 'success' && (
          <Box
            sx={{
              mb: 3,
              p: 3,
              backgroundColor: '#1f2937',
              border: '2px solid #10b981',
              borderRadius: '8px',
              textAlign: 'center'
            }}
          >
            <Typography
              variant="h6"
              sx={{
                color: '#10b981',
                fontWeight: 'bold'
              }}
            >
              Transferred funds - ${finalAmount.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
            </Typography>
          </Box>
        )}

        {transferStatus === 'cancelled' && (
          <Box
            sx={{
              mb: 3,
              p: 3,
              backgroundColor: '#1f2937',
              border: '2px solid #ef4444',
              borderRadius: '8px',
              textAlign: 'center'
            }}
          >
            <Typography
              variant="h6"
              sx={{
                color: '#ef4444',
                fontWeight: 'bold'
              }}
            >
              Cancelled Funds transfer
            </Typography>
          </Box>
        )}

        {transferStatus === 'idle' && requiredAmount > 0 && (
          <Alert severity="warning" sx={{ mb: 2 }}>
            Insufficient funds. You need ${requiredAmount.toFixed(2)} more to complete this trade.
          </Alert>
        )}

        {transferStatus === 'idle' && error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {transferStatus === 'idle' && success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        {/* Loading State */}
        {fetchingAccounts ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
            <CircularProgress sx={{ color: '#3b82f6' }} />
          </Box>
        ) : (
          <>
            {/* Bank Account Selection */}
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
                    disabled={transferStatus !== 'idle'}
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

            {/* No Bank Accounts */}
            {bankAccounts.length === 0 && (
              <Alert severity="info">
                No bank accounts found. Please contact support to add a bank account.
              </Alert>
            )}

            <Divider sx={{ my: 3, borderColor: '#4b5563' }} />

            {/* Transfer Amount */}
            <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 2, color: '#f1f5f9' }}>
              Transfer Amount
            </Typography>

            <TextField
              fullWidth
              type="number"
              label="Amount"
              value={transferAmount}
              onChange={(e) => setTransferAmount(Number(e.target.value))}
              disabled={transferStatus !== 'idle'}
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

            {/* Remaining Balance Preview */}
            {selectedAccount && (
              <Box sx={{ p: 2, backgroundColor: '#1f2937', border: '1px solid #4b5563', borderRadius: '8px', mb: 3 }}>
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

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 2 }}>
              <Button
                onClick={handleClear}
                disabled={loading}
                fullWidth
                sx={{
                  color: '#94a3b8',
                  borderColor: '#4b5563',
                  '&:hover': {
                    backgroundColor: '#374151',
                    borderColor: '#6b7280'
                  }
                }}
                variant="outlined"
              >
                Clear
              </Button>
              <Button
                onClick={handleTransfer}
                variant="contained"
                fullWidth
                disabled={loading || fetchingAccounts || bankAccounts.length === 0 || transferStatus !== 'idle'}
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
            </Box>
          </>
        )}
      </CardContent>
    </StyledCard>
  );
};

export default FundTransferPanel;
