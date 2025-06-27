// Email Notification Service for Agriport
// Handles email notifications for registration, urgent sales, reservations, etc.

class EmailService {
    constructor() {
        this.apiEndpoint = '/api/email';
        this.templates = {
            registration: this.getRegistrationTemplate(),
            urgentSale: this.getUrgentSaleTemplate(),
            reservation: this.getReservationTemplate(),
            reservationApproved: this.getReservationApprovedTemplate(),
            reservationRejected: this.getReservationRejectedTemplate(),
            adminAnnouncement: this.getAdminAnnouncementTemplate(),
            passwordReset: this.getPasswordResetTemplate(),
            saleConfirmation: this.getSaleConfirmationTemplate()
        };
    }
    
    // Send registration confirmation email
    async sendRegistrationConfirmation(userType, userData) {
        const template = this.templates.registration;
        const subject = `Welcome to Agriport - Your ${userType} Account is Ready!`;
        
        const emailData = {
            to: userData.email,
            subject: subject,
            html: template.replace(/{{(\w+)}}/g, (match, key) => userData[key] || ''),
            type: 'registration'
        };
        
        return this.sendEmail(emailData);
    }
    
    // Send urgent sale notification to all buyers
    async sendUrgentSaleNotification(urgentSale, buyers) {
        const template = this.templates.urgentSale;
        const subject = `🚨 Urgent Sale Alert: ${urgentSale.productName} at ${urgentSale.discountPercentage}% OFF!`;
        
        const emailPromises = buyers.map(buyer => {
            const emailData = {
                to: buyer.email,
                subject: subject,
                html: template.replace(/{{(\w+)}}/g, (match, key) => {
                    if (key === 'buyerName') return buyer.firstName;
                    return urgentSale[key] || '';
                }),
                type: 'urgent_sale'
            };
            return this.sendEmail(emailData);
        });
        
        return Promise.all(emailPromises);
    }
    
    // Send reservation notification to farmer
    async sendReservationNotification(reservation, farmer, buyer) {
        const template = this.templates.reservation;
        const subject = `New Reservation: ${buyer.firstName} wants to buy ${reservation.productName}`;
        
        const emailData = {
            to: farmer.email,
            subject: subject,
            html: template.replace(/{{(\w+)}}/g, (match, key) => {
                if (key === 'farmerName') return farmer.firstName;
                if (key === 'buyerName') return buyer.firstName;
                if (key === 'buyerPhone') return buyer.phone;
                return reservation[key] || '';
            }),
            type: 'reservation'
        };
        
        return this.sendEmail(emailData);
    }
    
    // Send reservation approval notification to buyer
    async sendReservationApproved(reservation, farmer, buyer) {
        const template = this.templates.reservationApproved;
        const subject = `Reservation Approved: ${reservation.productName}`;
        
        const emailData = {
            to: buyer.email,
            subject: subject,
            html: template.replace(/{{(\w+)}}/g, (match, key) => {
                if (key === 'buyerName') return buyer.firstName;
                if (key === 'farmerName') return farmer.firstName;
                if (key === 'farmerPhone') return farmer.phone;
                return reservation[key] || '';
            }),
            type: 'reservation_approved'
        };
        
        return this.sendEmail(emailData);
    }
    
    // Send reservation rejection notification to buyer
    async sendReservationRejected(reservation, farmer, buyer) {
        const template = this.templates.reservationRejected;
        const subject = `Reservation Update: ${reservation.productName}`;
        
        const emailData = {
            to: buyer.email,
            subject: subject,
            html: template.replace(/{{(\w+)}}/g, (match, key) => {
                if (key === 'buyerName') return buyer.firstName;
                if (key === 'farmerName') return farmer.firstName;
                return reservation[key] || '';
            }),
            type: 'reservation_rejected'
        };
        
        return this.sendEmail(emailData);
    }
    
    // Send admin announcement
    async sendAdminAnnouncement(announcement, recipients) {
        const template = this.templates.adminAnnouncement;
        const subject = announcement.subject;
        
        const emailPromises = recipients.map(recipient => {
            const emailData = {
                to: recipient.email,
                subject: subject,
                html: template.replace(/{{(\w+)}}/g, (match, key) => {
                    if (key === 'recipientName') return recipient.firstName;
                    return announcement[key] || '';
                }),
                type: 'admin_announcement'
            };
            return this.sendEmail(emailData);
        });
        
        return Promise.all(emailPromises);
    }
    
    // Send sale confirmation
    async sendSaleConfirmation(sale, farmer, buyer) {
        const template = this.templates.saleConfirmation;
        const subject = `Sale Confirmed: ${sale.productName}`;
        
        // Send to farmer
        const farmerEmailData = {
            to: farmer.email,
            subject: subject,
            html: template.replace(/{{(\w+)}}/g, (match, key) => {
                if (key === 'recipientName') return farmer.firstName;
                if (key === 'otherPartyName') return buyer.firstName;
                if (key === 'role') return 'seller';
                return sale[key] || '';
            }),
            type: 'sale_confirmation'
        };
        
        // Send to buyer
        const buyerEmailData = {
            to: buyer.email,
            subject: subject,
            html: template.replace(/{{(\w+)}}/g, (match, key) => {
                if (key === 'recipientName') return buyer.firstName;
                if (key === 'otherPartyName') return farmer.firstName;
                if (key === 'role') return 'buyer';
                return sale[key] || '';
            }),
            type: 'sale_confirmation'
        };
        
        return Promise.all([
            this.sendEmail(farmerEmailData),
            this.sendEmail(buyerEmailData)
        ]);
    }
    
    // Core email sending function
    async sendEmail(emailData) {
        try {
            const response = await fetch(this.apiEndpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${Auth.getToken()}`
                },
                body: JSON.stringify(emailData)
            });
            
            if (!response.ok) {
                throw new Error(`Email sending failed: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('Email sent successfully:', result);
            return result;
        } catch (error) {
            console.error('Error sending email:', error);
            throw error;
        }
    }
    
    // Email Templates
    getRegistrationTemplate() {
        return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Welcome to Agriport</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #2c5530; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .credentials { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
                .footer { text-align: center; padding: 20px; color: #666; }
                .btn { background: #2c5530; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Welcome to Agriport!</h1>
                </div>
                <div class="content">
                    <h2>Hello {{firstName}} {{lastName}},</h2>
                    <p>Congratulations! Your Agriport account has been successfully created.</p>
                    
                    <div class="credentials">
                        <h3>Your Login Credentials:</h3>
                        <p><strong>Email:</strong> {{email}}</p>
                        <p><strong>Password:</strong> {{password}}</p>
                        <p><strong>Account Type:</strong> {{userType}}</p>
                    </div>
                    
                    <p>For security reasons, we recommend changing your password after your first login.</p>
                    
                    <p style="text-align: center;">
                        <a href="{{loginUrl}}" class="btn">Login to Your Account</a>
                    </p>
                    
                    <p>If you have any questions, please don't hesitate to contact our support team.</p>
                </div>
                <div class="footer">
                    <p>&copy; 2024 Agriport. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        `;
    }
    
    getUrgentSaleTemplate() {
        return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Urgent Sale Alert</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .product { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; border-left: 4px solid #dc3545; }
                .price { font-size: 24px; color: #dc3545; font-weight: bold; }
                .original-price { text-decoration: line-through; color: #666; }
                .btn { background: #dc3545; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 Urgent Sale Alert!</h1>
                </div>
                <div class="content">
                    <h2>Hello {{buyerName}},</h2>
                    <p>A farmer has just posted an urgent sale with a great discount!</p>
                    
                    <div class="product">
                        <h3>{{productName}}</h3>
                        <p><strong>Quantity:</strong> {{quantity}} {{unit}}</p>
                        <p><strong>Location:</strong> {{location}}</p>
                        <p><strong>Best Before:</strong> {{bestBefore}}</p>
                        <p class="price">
                            <span class="original-price">{{originalPrice}} XAF</span>
                            <br>
                            Now: {{reducedPrice}} XAF
                        </p>
                        <p><strong>Reason:</strong> {{reason}}</p>
                    </div>
                    
                    <p>This is a limited-time offer. Act fast to secure this deal!</p>
                    
                    <p style="text-align: center;">
                        <a href="{{productUrl}}" class="btn">View Product</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        `;
    }
    
    getReservationTemplate() {
        return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>New Reservation</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #2c5530; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .reservation { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
                .btn { background: #2c5530; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; margin: 5px; }
                .btn-approve { background: #28a745; }
                .btn-reject { background: #dc3545; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>New Reservation Request</h1>
                </div>
                <div class="content">
                    <h2>Hello {{farmerName}},</h2>
                    <p>You have received a new reservation request!</p>
                    
                    <div class="reservation">
                        <h3>Reservation Details:</h3>
                        <p><strong>Product:</strong> {{productName}}</p>
                        <p><strong>Quantity:</strong> {{quantity}} {{unit}}</p>
                        <p><strong>Total Price:</strong> {{totalPrice}} XAF</p>
                        <p><strong>Buyer:</strong> {{buyerName}}</p>
                        <p><strong>Contact:</strong> {{buyerPhone}}</p>
                        <p><strong>Pickup Date:</strong> {{pickupDate}}</p>
                        <p><strong>Notes:</strong> {{notes}}</p>
                    </div>
                    
                    <p>Please review and respond to this reservation request.</p>
                    
                    <p style="text-align: center;">
                        <a href="{{approveUrl}}" class="btn btn-approve">Approve</a>
                        <a href="{{rejectUrl}}" class="btn btn-reject">Reject</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        `;
    }
    
    getReservationApprovedTemplate() {
        return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reservation Approved</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #28a745; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .reservation { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
                .btn { background: #28a745; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>✅ Reservation Approved!</h1>
                </div>
                <div class="content">
                    <h2>Great news, {{buyerName}}!</h2>
                    <p>Your reservation has been approved by the farmer.</p>
                    
                    <div class="reservation">
                        <h3>Reservation Details:</h3>
                        <p><strong>Product:</strong> {{productName}}</p>
                        <p><strong>Quantity:</strong> {{quantity}} {{unit}}</p>
                        <p><strong>Total Price:</strong> {{totalPrice}} XAF</p>
                        <p><strong>Farmer:</strong> {{farmerName}}</p>
                        <p><strong>Contact:</strong> {{farmerPhone}}</p>
                        <p><strong>Pickup Date:</strong> {{pickupDate}}</p>
                    </div>
                    
                    <p>Please contact the farmer to arrange payment and pickup details.</p>
                    
                    <p style="text-align: center;">
                        <a href="{{reservationUrl}}" class="btn">View Reservation</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        `;
    }
    
    getReservationRejectedTemplate() {
        return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Reservation Update</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #dc3545; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .btn { background: #2c5530; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; display: inline-block; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Reservation Update</h1>
                </div>
                <div class="content">
                    <h2>Hello {{buyerName}},</h2>
                    <p>Unfortunately, your reservation for {{productName}} could not be approved at this time.</p>
                    
                    <p>This could be due to:</p>
                    <ul>
                        <li>Product no longer available</li>
                        <li>Insufficient quantity</li>
                        <li>Scheduling conflicts</li>
                    </ul>
                    
                    <p>Don't worry! There are many other great products available on Agriport.</p>
                    
                    <p style="text-align: center;">
                        <a href="{{browseUrl}}" class="btn">Browse Products</a>
                    </p>
                </div>
            </div>
        </body>
        </html>
        `;
    }
    
    getAdminAnnouncementTemplate() {
        return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>{{subject}}</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #2c5530; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .announcement { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Agriport Announcement</h1>
                </div>
                <div class="content">
                    <h2>Hello {{recipientName}},</h2>
                    
                    <div class="announcement">
                        {{message}}
                    </div>
                    
                    <p>Thank you for being part of the Agriport community!</p>
                </div>
            </div>
        </body>
        </html>
        `;
    }
    
    getSaleConfirmationTemplate() {
        return `
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Sale Confirmation</title>
            <style>
                body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; }
                .container { max-width: 600px; margin: 0 auto; padding: 20px; }
                .header { background: #28a745; color: white; padding: 20px; text-align: center; }
                .content { padding: 20px; background: #f9f9f9; }
                .sale { background: white; padding: 15px; border-radius: 5px; margin: 15px 0; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Sale Confirmed!</h1>
                </div>
                <div class="content">
                    <h2>Hello {{recipientName}},</h2>
                    <p>Your sale has been successfully completed!</p>
                    
                    <div class="sale">
                        <h3>Sale Details:</h3>
                        <p><strong>Product:</strong> {{productName}}</p>
                        <p><strong>Quantity:</strong> {{quantity}} {{unit}}</p>
                        <p><strong>Total Amount:</strong> {{totalPrice}} XAF</p>
                        <p><strong>{{role === 'seller' ? 'Buyer' : 'Seller'}}:</strong> {{otherPartyName}}</p>
                        <p><strong>Date:</strong> {{saleDate}}</p>
                    </div>
                    
                    <p>Thank you for using Agriport!</p>
                </div>
            </div>
        </body>
        </html>
        `;
    }
}

// Initialize email service
window.EmailService = new EmailService();
